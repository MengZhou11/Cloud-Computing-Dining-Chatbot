import boto3
import time
import uuid
import json

def safeget(fn, default=None):
    try:
        return fn()
    except Exception:
        return default

class User:
    def __init__(self, event):
        self.event = event
        self.uuid = safeget(lambda: self.event["uuid"]) or str(uuid.uuid4())
        self.inputText = safeget(lambda: self.event["messages"][0]["unstructured"]["text"], "")
    
    def process(self):
        print("Start Session:", self.uuid)
        
        print("Input:", self.inputText)
        client = boto3.client('RestaurantRecommendationBot')
        response = client.recognize_text(
            botId='STHLVDLTXX',
            botAliasId='TSTALIASID',
            localeId='en_US',
            sessionId=self.uuid,
            text=self.inputText)
        
        responseIndent = safeget(lambda: response["sessionState"]["intent"]["slots"])
        print("Indent:", responseIndent)
        
        responseText = safeget(lambda: response["messages"][0]["content"])
        print("Text:", responseText)
        
        return [responseIndent, responseText]
        
    def pushSQS(self, indents):
        try:
            client = boto3.client("sqs")
            dynamodb = boto3.resource("dynamodb")
            table = dynamodb.Table("chatbot-user")
            response = table.put_item(
               Item={
                    'userid': self.uuid,
                    'info': indents,
                }
            )
            print("DB Response:", response)
            response = client.send_message(
                QueueUrl="https://us-east-1.amazonaws.com/565533802985/chatbot",
                MessageBody=json.dumps(indents)
            )
            print("SQS Response:", response)
        except Exception as err:
            print("SQSError:", err)
            return False
        return True
    
    def checkAndFinish(self, text, indents):
        valid = True
        normalizedIndents = {}
        for key in indents:
            val = safeget(lambda: indents[key]["value"]["interpretedValue"])
            if val:
                normalizedIndents[key] = val
            else:
                valid = False
        
        print("Validation:", valid, "Indents:", len(normalizedIndents))
        
        # indents are validated, push to queue
        if valid and len(normalizedIndents) > 0:
            self.pushSQS(normalizedIndents)
        return self.makeResponse(text, indents)
    
    def makeResponse(self, text="", indents=None):
        t = int(time.time())
        return {
            "uuid": self.uuid,
            "indents": indents,
            "input": self.inputText,
            "messages": [{
                "type": "unstructured",
                "unstructured": {
                    "id": t,
                    "text": text,
                    "timestamp": t,
                }
            }],
        }

errResponse = "Hi, welcome to our restautant recommendation bot. \n\nSend 'start' or 'begin' to start your journey."

def handler(event, context):
    user = User(event)
    try:
        [responseIndent, responseText] = user.process()
        if not responseIndent and not responseText:
            # request success but structure error, revoke current session and request a new one
            return user.makeResponse(errResponse)
        elif responseText:
            # got a good response text, return it to the frontend
            # if it is resumed from last session, append past info
            if user.inputText == "hello":
                resumedText = ""
                for key in responseIndent:
                    val = safeget(lambda: responseIndent[key]["value"]["interpretedValue"], "")
                    if val:
                        resumedText += f"{key}: {val}\n"
                if resumedText:
                    responseText = f"We have resumed your last session:\n\n{resumedText}\n{responseText}"
            return user.checkAndFinish(responseText, responseIndent)
        else:
            # got no message back, but receives indents
            return user.checkAndFinish("Unexpected happened.", responseIndent)
    except Exception as err:
        print("Error:", err)
        return user.makeResponse(errResponse)
