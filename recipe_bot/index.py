# /index.py

from flask import Flask, request, jsonify, render_template
import os
import dialogflow
import requests
import json
import pusher

pusher_client = pusher.Pusher(
    app_id=os.getenv('PUSHER_APP_ID'),
    key=os.getenv('PUSHER_APP_KEY'),
    secret=os.getenv('PUSHER_APP_SECRET'),
    cluster=os.getenv('PUSHER_APP_CLUSTER'),
    ssl=True)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def searchByName():
    data = request.get_json(silent=True)
    print(data)
    intent = data['queryResult']['intent']['displayName']
    parameters =data['queryResult']['parameters']

    api_key = os.getenv('MEALDB_API_KEY')

    reply = {}

    if intent == 'searchByName':
        name = parameters['dishName']

        dish_details = requests.get('https://www.themealdb.com/api/json/v1/{1}/search.php?s={0}'.format(name, api_key)).content
        dish_details = json.loads(dish_details)
        dish_details = dish_details['meals'][0]
        #print(dish_details['meals'][0]['strMeal'])
        #response =  """
        #    Dish : {0}
        #    Category: {1}
        #    YouTube: {2}
        #    Instructins: {3}
        #""".format(dish_details['meals'][0]['strMeal'], dish_details['meals'][0]['strCategory'], dish_details['meals'][0]['strYoutube'], dish_details['meals'][0]['strInstructions'])

        #reply = {
        #    "fulfillmentText": response,
        #}

        reply['payload'] = { "google": { "expectUserResponse": True,
                                        "richResponse": { "items": [ {"simpleResponse": {"textToSpeech": "One result for"+ dish_details['strMeal'] +"found:"}},
                                                                    {"basicCard": {"title": dish_details['strMeal'], 
                                                                                    "image": {"url": dish_details['strMealThumb'],"accessibilityText": "Dish Thumbnail"},
                                                                                    "buttons": [{"title": "YouTube Link", "openUrlAction": { "url": dish_details['strYoutube']}}],
                                                                                    "imageDisplayOptions": "WHITE",
                                                                                    "formattedText": "Instructions: " + dish_details['strInstructions'],
                                                                                    }
                                                                    }]
                                                        }
                                        }
                            }

    elif intent == 'searchRandom':
        dish_details = requests.get('https://www.themealdb.com/api/json/v1/{0}/random.php'.format(api_key)).content
        dish_details = json.loads(dish_details)
        dish_details = dish_details['meals'][0]

        reply['payload'] = { "google": { "expectUserResponse": True,
                                        "richResponse": { "items": [ {"simpleResponse": {"textToSpeech": "One result for"+ dish_details['strMeal'] +"found:"}},
                                                                    {"basicCard": {"title": dish_details['strMeal'], 
                                                                                    "image": {"url": dish_details['strMealThumb'],"accessibilityText": "Dish Thumbnail"},
                                                                                    "buttons": [{"title": "YouTube Link", "openUrlAction": { "url": dish_details['strYoutube']}}],
                                                                                    "imageDisplayOptions": "WHITE",
                                                                                    "formattedText": "Instructions: " + dish_details['strInstructions'],
                                                                                    }
                                                                    }]
                                                        }
                                        }
                            }

    elif intent == 'searchCategories':
        categories = requests.get('https://www.themealdb.com/api/json/v1/{0}/categories.php'.format(api_key)).content
        categories = json.loads(categories)
        categories = categories['categories']

        cateList = []
        for cate in categories[0:9]:
            cateList.append( {"optionInfo": {"key": cate['strCategory']}, "description": cate['strCategoryDescription'],
                            "image": {"url": cate['strCategoryThumb'],
                            "accessibilityText": "Thumbnail for " + cate['strCategory']},
                            "title": cate['strCategory']}
                            )

        reply['payload'] = {"google": {"expectUserResponse": True, 
                                        "richResponse": { "items": [{"simpleResponse": {"textToSpeech": "Choose a item"}}]},
                                        "systemIntent": {"intent": "actions.intent.OPTION", 
                                                        "data": {"@type": "type.googleapis.com/google.actions.v2.OptionValueSpec", 
                                                                "listSelect": { "title": "Categories",
                                                                                "items": cateList
                                                                            }
                                                                }
                                                        }
                                        }
                            }
                            
    elif intent == '':
        return reply
        

    return jsonify(reply)

def detect_intent_texts(project_id, session_id, text, language_code):
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, session_id)

    if text:
        text_input = dialogflow.types.TextInput(
            text=text, language_code=language_code)
            
        query_input = dialogflow.types.QueryInput(text=text_input)
        #print(query_input)
        response = session_client.detect_intent(
            session=session, query_input=query_input)
        #print(response)
        return response.query_result.fulfillment_text

@app.route('/send_message', methods=['POST'])
def send_message():
    message = request.form['message']
    project_id = os.getenv('DIALOGFLOW_PROJECT_ID')
    fulfillment_text = detect_intent_texts(project_id, "unique", message, 'en')
    response_text = { "message":  fulfillment_text }
    #print(response_text)
    #print(request.form['socketId'])
    #socketId = request.form['socketId']
    pusher_client.trigger('recipe_bot', 'new_message', 
                            {'human_message': message, 'bot_message': fulfillment_text})

    return jsonify(response_text)

# run Flask app
if __name__ == "__main__":
    app.run()