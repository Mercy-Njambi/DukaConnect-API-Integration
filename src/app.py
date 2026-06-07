from fastapi import FastAPI, HTTPException, Request
from src.schema import ProductCreate, OrderCreate, DescriptionRequest, PaymentRequest
from src.data import products_db, orders_db, orders_payments, payment_results
import os
import httpx
from dotenv import load_dotenv
import base64
from datetime import datetime
from google import genai


# Creating a FastAPI instance
app = FastAPI()

load_dotenv()

# config variables
gemini_api_key = os.getenv("gemini_api_key")
safaricom_consumer_key = os.getenv("safaricom_consumer_key")
safaricom_consumer_secret = os.getenv("safaricom_consumer_secret")
safaricom_passkey = os.getenv("safaricom_passkey")
businessShortCode = os.getenv("businessShortCode")
safaricom_callback_url = os.getenv("safaricom_callback_url")
PartyA = os.getenv("PartyA")
PartyB = os.getenv("PartyB")
PhoneNumber = os.getenv("PhoneNumber")

ai_client = genai.Client(api_key=gemini_api_key)

#--------------------------------------------------
# PRODUCTS ENDPOINTS
#--------------------------------------------------

# get all products
@app.get(path="/products", status_code=200)
def get_all_products():
    return products_db

# get one product
@app.get(path="/products/{product_id}", status_code=200)
def get_product(product_id:int):
    product = products_db.get(product_id)
    
    if not product:
        raise HTTPException(status_code=404, detail="Product not found!")
    
    return {"id":product_id, **product}

# create a new product
@app.post(path="/products", status_code=201)
def add_products(product:ProductCreate):
    
    next_id = max(products_db.keys(), default=0) + 1 
    products_db[next_id] = {
        "name": product.name,
        "price": product.price,
        "description": product.description
    }
    return {
        "message": "Product created successfully!",
        "product": {
            "id": next_id,
            **products_db[next_id]
        }
    }
#--------------------------------------------------
# ORDERS ENDPOINTS
#--------------------------------------------------  
@app.post(path="/orders", status_code=201)
def create_order(order:OrderCreate):
    if len(order.items) == 0:
        raise HTTPException(status_code=400, detail="Order must contain at least one product")
    
    total_amount = 0
    
    for item in order.items:
        product = products_db.get(item.product_id)
        
        if not product:
            raise HTTPException(status_code=404, detail=f"product {item.product_id} not found!")
        
        total_amount += (product['price'] * item.quantity)
        
    new_order_id = len(orders_db) + 1
    
    orders_db[new_order_id] = {
        "items": [{"product_id": item.product_id, "quantity": item.quantity} for item in order.items],
        "total_amount": total_amount
    }
    
    return {
        "message" : "Order created successfully!",
        "order_id" : new_order_id,
        **orders_db[new_order_id]
    }
    
@app.get(path="/orders/{order_id}", status_code=200)
def get_order(order_id:int):
    order = orders_db.get(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "order_id" : order_id,
        **order
    }

#--------------------------------------------------
# GEMINI API INTERGRATION
#--------------------------------------------------  

@app.post("/generate-description")
async def generate_description(data: DescriptionRequest):
    if not gemini_api_key:
        raise HTTPException(status_code=500, detail="Server configuration error: GEMINI_API_KEY is missing.")

    prompt = f"""
    Write a short, catchy product description for:
    Product Name: {data.product_name}
    Keywords: {", ".join(data.keywords)}
    Keep it under 50 words.
    """
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                # "https://googleapis.com",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
                headers={
                    "x-goog-api-key": gemini_api_key,
                    "Content-Type": "application/json"
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt}
                            ]
                        }
                    ]
                }
            )

            response.raise_for_status()
            result = response.json()

            generated_text = result["candidates"][0]["content"]["parts"][0]["text"]

            return {
                "product_name": data.product_name,
                "generated_description": generated_text.strip()
            }

        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=response.status_code, detail=f"Gemini API returned an error: {response.text}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Gemini API request failed: {str(e)}")

#--------------------------------------------------
# MPESA HELPER FUNCTIONS
#-------------------------------------------------- 
async def generate_access_token():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
            auth=(
                safaricom_consumer_key,
                safaricom_consumer_secret
            )
        )

        response.raise_for_status()

        return response.json()["access_token"]
    
def generate_password():

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password_string = (businessShortCode + safaricom_passkey + timestamp)

    password = base64.b64encode(password_string.encode()).decode()

    return password, timestamp

def generate_thank_you_message(phone_number: str, order_id: str, amount: str) -> str:

    prompt = (
        f"Write a warm, professional order confirmation and thank you message to a retail customer. "
        f"Keep it brief (around 2 to 3 sentences). "
        f"Do not use generic brackets or placeholders like [Customer Name]. "
        f"Incorporate these exact live details cleanly into the prose:\n"
        f"- Customer phone/account: {phone_number}\n"
        f"- Order reference number: {order_id}\n"
        f"- Amount paid: KES {amount}"
    )
    
    try:
        ai_response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return ai_response.text.strip()
    except Exception as ai_err:
        print(f"Gemini generation failed, falling back to template: {ai_err}")
        # Reliable fallback string if the API is unreachable or times out
        return (
            f"Thank you for your business! We have successfully processed your payment of "
            f"KES {amount} for order reference {order_id}."
        )

#--------------------------------------------------
# MPESA ENDPOINTS
#-------------------------------------------------- 

@app.post("/pay", status_code=200)
async def stk_push(payment: PaymentRequest):
    order = orders_db.get(payment.order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail=f"Order {payment.order_id} not found in the system. Please recheck.")
    
    amount_to_pay = order.get("total_amount")
    
    try:

        access_token = await generate_access_token()
        password, timestamp = generate_password()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                json={
                    "BusinessShortCode": businessShortCode,
                    "Password": password,
                    "Timestamp": timestamp,
                    "TransactionType": "CustomerPayBillOnline",
                    "Amount": int(amount_to_pay),
                    "PartyA": PartyA,
                    "PartyB": PartyB,
                    "PhoneNumber": payment.phone_number,
                    "CallBackURL": safaricom_callback_url,
                    "AccountReference": "DukaConnect",
                    "TransactionDesc": f"Payment for order{order}"
                }
            )

            response.raise_for_status()
            stk_response = response.json()
            checkout_request_id = stk_response["CheckoutRequestID"]

            orders_payments[checkout_request_id] = {
                "phone_number": payment.phone_number,
                "amount": amount_to_pay,
                "order_id" : payment.order_id
            }

            return stk_response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STK Push failed: {str(e)}")


@app.post("/callback")
async def mpesa_callback(request: Request):
    # print("\n===== M-PESA RAW CALLBACK INTEGRATION =====")
    
    # Read raw bytes first to see exactly what Safaricom sent
    raw_body = await request.body()
    decoded_body = raw_body.decode("utf-8")
    # print("Raw Body Received:", decoded_body)
    
    try:
        # Try converting it to JSON manually
        import json
        callback_data = json.loads(decoded_body)
        
        stk_callback = callback_data["Body"]["stkCallback"]
        checkout_request_id = stk_callback["CheckoutRequestID"]
        result_code = stk_callback["ResultCode"]
        result_desc = stk_callback["ResultDesc"]
        
        payment_results[checkout_request_id] = {
            "result_code": result_code,
            "result_description": result_desc
        }        
        # print(f"Success parsing: {checkout_request_id} - {result_code}")
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    except Exception as e:
        print("Parsing failed. Error details:", str(e))
        return {"ResultCode": 1, "ResultDesc": "Invalid JSON Payload structure"}

@app.get("/payment-status/{checkout_request_id}")
async def payment_status(checkout_request_id: str):
    try:
        access_token = await generate_access_token()
        password, timestamp = generate_password()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://sandbox.safaricom.co.ke/mpesa/stkpushquery/v1/query",
                headers={
                    "Authorization": f"Bearer {access_token}"
                },
                json={
                    "BusinessShortCode": businessShortCode,
                    "Password": password,
                    "Timestamp": timestamp,
                    "CheckoutRequestID": checkout_request_id
                }
            )

            result = response.json()
            # print(result)

            payment_info = orders_payments.get(checkout_request_id,{})

            if result.get("ResultCode") == "0":

                thank_you_message = generate_thank_you_message(
                    payment_info.get("phone_number"),
                    payment_info.get("order_id"),
                    payment_info.get("amount")
                )

                return {
                    "payment_status": "SUCCESS",
                    "mpesa_response": result,
                    "thank_you_message": thank_you_message
                }

            return {
                "payment_status": "PENDING_OR_FAILED",
                "mpesa_response": result
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status query failed: {str(e)}")
        
@app.get("/payment-result/{checkout_request_id}")
def get_payment_result(checkout_request_id: str):
    result = payment_results.get(checkout_request_id)

    if not result:
        raise HTTPException(status_code=404, detail="Payment result not found")

    return result
