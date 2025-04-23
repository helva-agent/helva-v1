import gradio as gr
from gradio import ChatMessage
from web3 import Web3
from dotenv import load_dotenv
import os
import re
from langchain_openai import ChatOpenAI  # ✅ Corrected import
from langchain.schema import SystemMessage, HumanMessage
from langchain.agents import initialize_agent, AgentType
from langchain.tools import Tool

# Load environment variables
load_dotenv()
RPC_URL = os.getenv("RPC_URL")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
MY_ADDRESS = os.getenv("MY_ADDRESS")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Connect to Web3 provider
web3 = Web3(Web3.HTTPProvider(RPC_URL))
if not web3.is_connected():
    raise Exception("Web3 connection failed!")

# Initialize LangChain LLM (GPT-4) ✅ Using new import
llm = ChatOpenAI(model_name="gpt-4", temperature=0, openai_api_key=OPENAI_API_KEY)

# Function to extract amount and address using LLM
def extract_transaction_details(user_input):
    system_prompt = """You are an AI assistant that extracts transaction details from natural language text. 
    Given a user input, extract the amount of HBAR and the recipient Ethereum address (0x...).
    If the input does not contain both, return 'Invalid transaction request'.
    
    Example Inputs:
    - "Send 50 HBAR to 0x123..."
    - "I want to transfer 25 HBAR to 0x456..."
    - "Can you please send 10 HBAR to 0x789?"

    Format Output:
    - If valid: "Amount: <amount> HBAR, Address: <address>"
    - If invalid: "Invalid transaction request"
    """

    # ✅ Using invoke() instead of the deprecated __call__()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_input)
    ]

    response = llm.invoke(messages) 
    return response.content if hasattr(response, "content") else str(response)  # ✅ Ensure it's a string

# Function to send HBAR transaction
def send_hbar_transaction(user_input):
    extracted_info = extract_transaction_details(user_input)

    if "Invalid transaction request" in extracted_info:
        return "⚠️ Sorry, I couldn't extract the amount and address. Please try again with a valid request."

    # Extract values from LLM response
    match = re.search(r"Amount: (\d+(\.\d+)?) HBAR, Address: (0x[a-fA-F0-9]{40})", extracted_info)
    if not match:
        return "❌ Error parsing transaction details."

    amount_hbar = float(match.group(1))
    receiver_address = Web3.to_checksum_address(match.group(3))  # ✅ Convert to checksum address

    # ✅ Ensure the address is valid before proceeding
    if not Web3.is_address(receiver_address):
        return f"❌ Invalid Ethereum address: {receiver_address}"

    try:
        amount_wei = web3.to_wei(amount_hbar, 'ether')
        nonce = web3.eth.get_transaction_count(MY_ADDRESS)

        tx = {
            'nonce': nonce,
            'to': receiver_address,
            'value': amount_wei,
            'gas': 3000000,
            'gasPrice': web3.eth.gas_price
        }

        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        return f"✅ Transaction Successful! Hash: {web3.to_hex(tx_hash)}"
    except Exception as e:
        return f"❌ Transaction failed: {str(e)}"


def chatbot(user_input, chat_history=None):
    # ✅ Ensure chat_history is initialized correctly
    if chat_history is None:
        chat_history = []

    # ✅ Send transaction and store response
    response = send_hbar_transaction(user_input)
    chat_history = [response]
    
    return chat_history
    

# ✅ Set `type='messages'` to avoid warnings
iface = gr.ChatInterface(
    fn=chatbot,
    title="HBAR Agent",
    chatbot=gr.Chatbot(type="messages"),  # ✅ Fix for Gradio deprecation warning
    textbox=gr.Textbox(placeholder="Type your transaction request...")
)

# Launch Gradio App
if __name__ == "__main__":
    iface.launch()
##Try any random address you want. Example:
##0xFAe2dac0686f0e543704345aEBBe0AEcab4EDA3d
##0x472e78859dcd440bfa657062b4eb666a0d97cafa
