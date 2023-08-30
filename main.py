import math
import boto3
# Importing the PIL library
from io import BytesIO
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import io

s3_client = boto3.client('s3')
textract_client = boto3.client('textract')


def translate_with_gpt(original_text):
    # translate text
    translated_text = "translated"
    return translated_text

def geometry_analyzer(textract_response):
    line_blocks = [block for block in textract_response['Blocks'] if block['BlockType'] == 'LINE']
    
    line_info_list = []
    for block in line_blocks:
        text = block['Text']
        bounding_box = block['Geometry']['BoundingBox']
        
        line_info = {'Text': text, 'BoundingBox': bounding_box}
        line_info_list.append(line_info)
    
    return line_info_list


def image_editer(file_byte_string, translated_text_info_list):
    # Open an Image
    img = Image.open(BytesIO(file_byte_string))

    # get sizes
    img_width, img_height = img.size
    
    # Call draw Method to add 2D graphics in an image
    I1 = ImageDraw.Draw(img)

    for info in translated_text_info_list:
        # get coordinates from text_info_list
        anchor_x = info['BoundingBox']['Left']
        anchor_y = info['BoundingBox']['Top']
        txt_width = info['BoundingBox']['Width']
        txt_height = info['BoundingBox']['Height']


        # add rectangles on top of the original text
        I1.rectangle(
            [(img_width*anchor_x - txt_width*img_width*0.1, img_height*anchor_y), ((img_width*anchor_x + txt_width*img_width + txt_width*img_width*0.1), (img_height*anchor_y + txt_height*img_height))], fill=(255, 0, 0)
        )


        # text management
        translated_txt = info['Text']
        translated_txt_len = len(translated_txt)

        # the text has to be smaller than the height and width of the box
        if (math.floor(txt_width*img_width/translated_txt_len) < math.floor(img_height*txt_height)):
            font_size = math.floor(txt_width*img_width/translated_txt_len*2.5)  # for some reason calculated font size doesnt match WITHOUT *2.5
        else:
            font_size = math.floor(img_height*txt_height)
            print("size got determined based on the height")

        # Custom font style and font size
        myFont = ImageFont.truetype('fonts/Helvetica.ttf',font_size)

        
        
        # Add Text to an image
        I1.text((img_width*anchor_x+(img_width*txt_width)/2, img_height*anchor_y+(img_height*txt_height)/2), translated_txt, font=myFont, fill=(1, 0, 0), anchor='mm')
    
    # Display edited image
    #img.show()
    
    # Save the edited image
    #img.save("images/lancs2.png")

    # Save the image to an in-memory file
    in_mem_file = io.BytesIO()
    img.save(in_mem_file, format=img.format)
    in_mem_file.seek(0)


    return in_mem_file


def lambda_handler(event, context):
    print(event)
    # get bucket and key
    original_bucket = event['Records'][0]['s3']['bucket']['name']
    original_key = event['Records'][0]['s3']['object']['key']

    print(original_bucket)
    print(original_key)
    
    
    # return json.loads(body.decode('utf-8'))

   

    # textract
    textract_response = textract_client.analyze_document(
            Document={'S3Object': {'Bucket': original_bucket, 'Name': original_key}},
            FeatureTypes=['TABLES'])
    print(textract_response)
    text_info_list = geometry_analyzer(textract_response)

    print(*text_info_list)

    # translate the text and update text_info_list
    for index, info in enumerate(text_info_list):
        original_text = info['Text']
        translated_text = translate_with_gpt(original_text)
        text_info_list[index]['Text'] = translated_text
    translated_text_info_list = text_info_list

    print(*translated_text_info_list)

    # get image from s3
    response = s3_client.get_object(Bucket=original_bucket, Key=original_key)
    body = response['Body'].read()


    # pass the image it got from s3 to the image manipulation fucnc
    edited_img = image_editer(body, translated_text_info_list)

    # save the edited image to another bucket
    new_bucket = 'textract-result-py'
    new_key = 'test.png'

    response = s3_client.upload_fileobj(
        edited_img, # This is what i am trying to upload
        new_bucket,
        new_key
    )

    print(response)


    