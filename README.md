## Architecture & Workflow

Here’s how the bot works at a high level:

1. **Profile Ingestion**  
   Read and parse LinkedIn profile pdf 
2. **Push Message**  
    It uses Pushover https://pushover.net/, to push message to mobile by using tools
3. **Question Processing**  
   When a user asks a question, the system:  
   - Encodes the question  
   - Compares with profile embeddings or a knowledge base  
   - Generates a contextually relevant answer  
4. **Answer Generation**  
   Using a language model ( GPT), the bot crafts a response grounded in the profile context.  

You can extend or adapt each component (e.g. change embedding method or LLM backend).

## Installation & Setup

Below are steps to get the bot running locally.

```bash
# Clone the repo
git clone https://github.com/safalmahat/my-career-conversation-bot.git
cd my-career-conversation-bot

# (Optional) create & activate virtual environment
python3 -m venv venv
source venv/bin/activate   # on Mac / Linux
# venv\Scripts\activate   # on Windows

# Install dependencies
pip install -r requirements.txt


Once installed, you can run:
    python main.py