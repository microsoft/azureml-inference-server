from azureml.contrib.services.aml_request import AMLRequest, rawhttp 
from azureml.contrib.services.aml_response import AMLResponse 
import time, logging, json


def init():  
    print("Init complete")

def generate(items): 
    for item in items: 
        print("test")
        time.sleep(1) 
        yield 'item: ' + str(item) + '\n\n' 

@rawhttp 
def run(request : AMLRequest): 
    logging.info("model 1: request received") 
    data = request.data 
    print(request.get_data()) 
    items = json.loads(data)["items"] 
    return AMLResponse(generate(items), 200)