# 環境変数
# LINE_CHANNEL_ACCESS_TOKEN
# LINE_CHANNEL_SECRET
# S3PATH

import json  
import os  
import logging  
import urllib.request
import base64  
import hashlib  
import hmac
import boto3
import sys
from boto3.dynamodb.conditions import Key, Attr
import ast
import random
import math
import time
import datetime

# ログ出力の準備  
logger = logging.getLogger()  
logger.setLevel(logging.INFO)  

dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):  
    channel_secret = os.environ['LINE_CHANNEL_SECRET']  
    hash = hmac.new(channel_secret.encode('utf-8'), event['body'].encode('utf-8'), hashlib.sha256).digest()  
    signature = base64.b64encode(hash)  

    xLineSignature = event['headers']['X-Line-Signature'].encode('utf-8')  
    if xLineSignature != signature:  
        logger.info('署名の不一致')  
        return ''

    body = json.loads(event['body'])
    
    for event in body['events']:  
        logger.info('[Debug] event = {0}'.format(event) )
        if event['type'] == 'message':  
            if event['message']['type'] == 'text':
                if event['message']['text'].startswith('menu'):
                    show_menu(event)
                elif event['message']['text'].startswith('メニュ'):
                    show_menu(event)
                elif event['message']['text'].startswith(':Q:'):
                    put_Question(event)
                else:
                    exec_reply(event, event['message']['text'])
        elif event['type'] == 'postback':
            if event['postback']['data'] == "menu-top":
                show_menu(event)
            if event['postback']['data'] == "menu-quest":
                show_QuestFlow(event)
            if event['postback']['data'] == "menu-result":
                show_Result(event)
            if event['postback']['data'] == "menu-howtoput":
                show_HowToPut(event)
            if event['postback']['data'].startswith("{'ans'"):
                ans = ast.literal_eval( event['postback']['data'] )
                show_ResultFlow(event, ans)
    return 0
##################################################

def show_menu(event):
    
    altText="menu"
    thumbnailImageUrl = os.environ['S3PATH'] + "top.png"
    title="AWS暗記カード"
    textStr="メニュー"
    label01="テスト"
    label02="成績"
    label03="登録の説明"
    data01="menu-quest"
    data02="menu-result"
    data03="menu-howtoput"

    messages = []
    messages.append({
      "type": "template",
      "altText": altText,
      "template": {
          "type": "buttons",
          "thumbnailImageUrl": thumbnailImageUrl,
          "imageAspectRatio": "rectangle",
          "imageSize": "cover",
          "imageBackgroundColor": "#FFFFFF",
          "title": title,
          "text": textStr,
          "defaultAction": {
                "type": "postback",
                "label": "メニュー",
                "data": "menu-top"
          },
          "actions": [
              {
                "type": "postback",
                "label": label01,
                "data": data01
              },
              {
                "type": "postback",
                "label": label02,
                "data": data02
              },
              {
                "type": "postback",
                "label": label03,
                "data": data03
              }
          ]
      }
    })  

    url = 'https://api.line.me/v2/bot/message/reply'  
    headers = {  
        'Content-Type': 'application/json',  
        'Authorization': 'Bearer ' + os.environ['LINE_CHANNEL_ACCESS_TOKEN']  
        }  
    data = {  
        'replyToken': event['replyToken'],
        'messages': messages  
    }
    request = urllib.request.Request(url, data = json.dumps(data).encode('utf-8'), method = 'POST', headers = headers) 
    with urllib.request.urlopen(request) as response:
        logger.info(response.read().decode("utf-8"))

def show_ResultFlow(event, ans):
    imgdict = {
        'OK': os.environ['S3PATH'] + 'OK.png', 
        'NG': os.environ['S3PATH'] + 'NG.png'
    }
    
    txtdict = {
        'OK': "そのとーり！",
        'NG': "むむっ、それはちがう・・"
    }

    args = {
        'tablename':  'results',
        'userid':     event['source']['userId'],
        'by_at':      ans['by_at'],
        'category':   ans['category'],
        'start_date': ans['start_date'],
        'end_date':   event['timestamp'],
        'result':     ans['ans']
    }
    put_result(args)

    label01 = '次の問題'
    label02 = 'メニュー'
    label03 = '成績'
    data01 = 'menu-quest'
    data02 = 'menu-top'
    data03 = 'menu-result'

    d = {
        'altText': 'result',
        'thumbnailImageUrl': imgdict[ ans['ans'] ],
        'title': '結果',
        'textVal': txtdict[ ans['ans'] ] + "正解は『 " + str(ans['correct_answer']) + " 』",
        'label01': label01,
        'label02': label02,
        'label03': label03,
        'data01' : data01,
        'data02' : data02,
        'data03' : data03
    }
    #logger.info(d)
    show_buttonTemplate(event, d)
    return 0

def show_QuestFlow(event):
    
    sArgs = {
        'tablename': 'questions',
        'key1'     : 'category',
        'keyVal1'  : 'aws',
        'key2'     : 'put_date'
    }
    
    quest = select_question(sArgs)

    no = random.randint(1, len(quest["Items"]) ) - 1
    thumbnailImageUrl = os.environ['S3PATH'] + quest["Items"][no]["img"]
    
    textVal = quest["Items"][no]["Q"]
    comStr  = "'category': '" + quest["Items"][no]["category"] + "'"
    comStr += ",'by_at': '" + quest["Items"][no]["by_at"] + "'"
    comStr += ",'start_date': '" + str(math.floor( time.time()*1000 ) ) + "'"
    comStr += ",'correct_answer': '" + quest["Items"][no]["OK"] + "'"

    selectTmp = [ quest["Items"][no]["OK"] +"-OK", quest["Items"][no]["NG1"] +"-NG", quest["Items"][no]["NG2"] +"-NG"]
    random.shuffle(selectTmp)

    label01 = selectTmp[0].split('-')[0]
    label02 = selectTmp[1].split('-')[0]
    label03 = selectTmp[2].split('-')[0]
    data01  = "{'ans': '" + selectTmp[0].split('-')[1] + "'," + comStr + "}"
    data02  = "{'ans': '" + selectTmp[1].split('-')[1] + "'," + comStr + "}"
    data03  = "{'ans': '" + selectTmp[2].split('-')[1] + "'," + comStr + "}"

    d = {
        'altText': 'question',
        'thumbnailImageUrl': thumbnailImageUrl,
        'title': '問題',
        'textVal': textVal,
        'label01': label01,
        'label02': label02,
        'label03': label03,
        'data01' : data01,
        'data02' : data02,
        'data03' : data03
    }
    logger.info( d )
    show_buttonTemplate(event, d)
    return 0

def show_buttonTemplate(event, d):
    altText=d["altText"]
    thumbnailImageUrl=d["thumbnailImageUrl"]
    title=d["title"]
    textVal=d["textVal"]
    label01=d["label01"]
    label02=d["label02"]
    label03=d["label03"]
    data01=d["data01"]
    data02=d["data02"]
    data03=d["data03"]
    
    messages = []
    messages.append({
      "type": "template",
      "altText": altText,
      "template": {
          "type": "buttons",
          "thumbnailImageUrl": thumbnailImageUrl,
          "imageAspectRatio": "rectangle",
          "imageSize": "cover",
          "imageBackgroundColor": "#FFFFFF",
          "title": title,
          "text": textVal,
          "defaultAction": {
                "type": "postback",
                "label": "メニュー",
                "data": "menu-top"
          },
          "actions": [
              {
                "type": "postback",
                "label": label01,
                "data": data01
              },
              {
                "type": "postback",
                "label": label02,
                "data": data02
              },
              {
                "type": "postback",
                "label": label03,
                "data": data03
              }
          ]
      }
    })
    url = 'https://api.line.me/v2/bot/message/reply'  
    headers = {  
        'Content-Type': 'application/json',  
        'Authorization': 'Bearer ' + os.environ['LINE_CHANNEL_ACCESS_TOKEN']  
        }  
    data = {  
        'replyToken': event['replyToken'],  
        'messages': messages  
    }  
    request = urllib.request.Request(url, data = json.dumps(data).encode('utf-8'), method = 'POST', headers = headers) 
    with urllib.request.urlopen(request) as response:
        logger.info(response.read().decode("utf-8"))

    return 0


def exec_reply(event, msg):
    messages = []
    messages.append({  
            'type': 'text',  
            'text': msg
        })  

    url = 'https://api.line.me/v2/bot/message/reply'  
    headers = {  
        'Content-Type': 'application/json',  
        'Authorization': 'Bearer ' + os.environ['LINE_CHANNEL_ACCESS_TOKEN']  
        }  
    data = {  
        'replyToken': event['replyToken'],  
        'messages': messages  
    }  
    request = urllib.request.Request(url, data = json.dumps(data).encode('utf-8'), method = 'POST', headers = headers) 
    with urllib.request.urlopen(request) as response:
        logger.info(response.read().decode("utf-8"))



def select_question(args):
    tablename = args["tablename"]
    key1      = args["key1"]
    keyVal1   = args["keyVal1"]
    key2      = args["key2"]

    bwnStart = [20200666000000, 20200777000000, 20200815000000]
    bwnRange = [500000, 600000, 700000, 800000, 900000, 1000000, 2000000, 3000000, 4000000, 5000000, 6000000, 7000000, 8000000, 9000000, 10000000]

    random.shuffle(bwnStart)
    random.shuffle(bwnRange)
    
    bwnEnd = bwnStart[0] + bwnRange[0]
    
    print( "between {0} , {1}".format(bwnStart[0] , bwnEnd) )
    print( key2 )
    
    table    = dynamodb.Table( tablename )

    response = table.query(
        KeyConditionExpression=Key(key1).eq(keyVal1), 
        FilterExpression = Key(key2).between( bwnStart[0], bwnEnd )
    )
    logger.info( "-- selected response --" )
    logger.info( str(len(response["Items"])) )

    return response    


def get_question(tablename, id):
    table    = dynamodb.Table( tablename )
    response = table.get_item(
            Key={
                 'id': id
            }
        )
    return response['Item']


def put_result(d):
    tablename  = d['tablename']
    userid     = d['userid']
    by_at      = d['by_at']
    category   = d['category']
    start_date = int(d['start_date'])
    end_date   = int(d['end_date'])
    timetoans  = int(end_date - start_date)
    result     = d['result']
    
    table = dynamodb.Table( tablename )
    item = {
        "userid":         userid,
        "by_at":          by_at,
        "category":       category,
        "start_date":     start_date,
        "end_date":       end_date,
        "time_to_answer": timetoans,
        "result":         result
    }
    table.put_item(Item=item)
    return 0


def put_Question(event):
    putFlg = 1
    msg = ""

    userid = event['source']['userId']
    timestamp = int( datetime.datetime.fromtimestamp( event['timestamp']/1000 ).strftime("%Y%m%d%H%M%S") )
    
    if len(event['message']['text'].split(':Q:')) <= 2:
        msg += "『 :Q: xxx :Q: 』"
        putFlg = 0
    if len(event['message']['text'].split(':OK:')) <= 2:
        msg += "『 :OK: xxx :OK: 』"
        putFlg = 0
    if len(event['message']['text'].split(':NG1:')) <= 2:
        msg += "『 :NG1: xxx :NG1: 』"
        putFlg = 0
    if len(event['message']['text'].split(':NG2:')) <= 2:
        msg += "『 :NG2: xxx :NG2: 』"
        putFlg = 0
    
    if putFlg == 0:
        msg = "登録できません。" + msg + " が不足しています"
        exec_reply(event, msg)
        return 0

    Qstr  = event['message']['text'].split(':Q:')[1]
    OKstr = event['message']['text'].split(':OK:')[1]
    NG1str= event['message']['text'].split(':NG1:')[1]
    NG2str= event['message']['text'].split(':NG2:')[1]

    item = {
        "by_at": userid + "_" + str(timestamp),
        "category": "aws",
        "img": "quest-posting.png",
        "NG1": NG1str,
        "NG2": NG2str,
        "OK" : OKstr,
        "put_date" : timestamp,
        "Q": Qstr,
        "userid": userid 
    }

    for key in item:
        logger.info( item[key] )
        if len( str(item[key]) ) <= 0:
            putFlg = 0
            msg += "『 " + key + " 』"

    if putFlg == 1:
        table = dynamodb.Table( 'questions' )
        table.put_item(Item=item)
        exec_reply(event, "問題を登録しました")
    else:
        msg = "登録できません。" + msg + " が不足しています"
        exec_reply(event, msg)
    return 0


def show_Result(event):
    userid = event['source']['userId']

    table = dynamodb.Table( 'results' )
    response = table.query(
        KeyConditionExpression = Key('userid').eq( userid )
    )
    
    count_OK = 0
    total_Time = 0
    for item in response['Items']:
        if item['result'] == 'OK':
            count_OK += 1
        
        total_Time += item['time_to_answer']
    
    ok_Rate   = math.floor( count_OK/len(response['Items'] )*100*10)/10
    mean_Time = math.floor( total_Time / len(response['Items'])/1000 *10 )/10

    msg = ""
    msg+= "正解率: " + str( ok_Rate ) + "% (" + str( count_OK ) + "/" + str( len(response['Items']) ) +")\n"
    msg+= "回答までの平均時間: " + str( mean_Time ) + "秒"

    thumbnailImageUrl= os.environ['S3PATH'] + "status.png"
    title = "成績"
    label01="テスト"
    label02="メニュー"
    label03="登録の説明"
    data01="menu-quest"
    data02="menu-top"
    data03="menu-howtoput"

    d = {
        'altText': 'result',
        'thumbnailImageUrl': thumbnailImageUrl,
        'title': title,
        'textVal': msg,
        'label01': label01,
        'label02': label02,
        'label03': label03,
        'data01' : data01,
        'data02' : data02,
        'data03' : data03
    }
    logger.info(d)
    show_buttonTemplate(event, d)

    return 0

def show_HowToPut(event):
    
    thumbnailImageUrl= os.environ['S3PATH'] + "howtoput.png"
    title="問題を登録する方法"
    label01="テスト"
    label02="メニュー"
    label03="登録の説明"
    data01="menu-quest"
    data02="menu-top"
    data03="menu-howtoput"
    textVal="上図の規則でメッセージを送ります。(できるだけ文章を短く)"

    d = {
        'altText': 'result',
        'thumbnailImageUrl': thumbnailImageUrl,
        'title':   title,
        'textVal': textVal,
        'label01': label01,
        'label02': label02,
        'label03': label03,
        'data01' : data01,
        'data02' : data02,
        'data03' : data03
    }
    logger.info(d)
    show_buttonTemplate(event, d)

    return 0
