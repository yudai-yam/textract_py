import math
import boto3
# Importing the PIL library
from io import BytesIO
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont

import constants
import io
# Import the os package
import os

# Import the openai package
import openai

s3_client = boto3.client('s3')
textract_client = boto3.client('textract')
openai.api_key = constants.API_KEY


current_block_info_storage = [] # store the current block info that are in the same chunk, this is used only in the block_relation_checker
txt_line_storage = [] # store the full text and its number of LINEs, this is used throughout the program


# identify text block
def block_relation_checker(anchor_x, anchor_y, block_height, text, last):
    global current_block_info_storage
    global txt_line_storage

    print("the text being examined is "+text)
    

    if (current_block_info_storage == []): # the very first line
        block_info = [anchor_x, anchor_y, block_height, text]
        current_block_info_storage.append(block_info)
        print("it's the very first sentence")
    
    else: # not the very first line
        # check the space in between two texts (blocks)
        print("this is not the first sentence")
        prev_anchor_y = current_block_info_storage[-1][1]
        prev_block_height = current_block_info_storage[-1][2]
        space = anchor_y - (prev_anchor_y + prev_block_height) # represented by ratio against the original img size

        if (space > block_height):
            print("space>block")
            # belongs to another block
            # combine existing texts for translation
            combined_text = ' '.join(block_info[3] for block_info in current_block_info_storage)
            # store the number of LINE in a single block
            num_of_line = len(current_block_info_storage)

            txt_line_storage.append([combined_text, num_of_line])
            print("the text being appended is" + combined_text)
            # start from scratch
            current_block_info_storage = []

            if (last == True):
                txt_line_storage.append([text, 1])
                print("last element detected")

            block_info = [anchor_x, anchor_y, block_height, text]
            current_block_info_storage.append(block_info)   

        elif (space <= block_height):
            block_info = [anchor_x, anchor_y, block_height, text]
            current_block_info_storage.append(block_info)  

            if (last == True):
                print("last element detected")

                # combine existing texts for translation
                combined_text = ' '.join(block_info[3] for block_info in current_block_info_storage)
                # store the number of LINE in a single block
                num_of_line = len(current_block_info_storage)

                txt_line_storage.append([combined_text, num_of_line])


    print("the current block info storage is")
    print(*current_block_info_storage)
    print("the txt_line_storage is")
    print(*txt_line_storage)



    #TODO check if it's in the same parallel line



def translate_with_gpt(original_texts):
    # Define the system message
    system_msg = 'You are a helpful tranlator.'

    # Define the user message
    #user_msg = f'''Simply translate this text into Spainsh. The text is: '
                #+ {original_text}
                #+ '.\nIf this text is incomplete, just return "INCMP" instead of translating. Note that just a noun is considered complete, even without an article.'''
    
    user_msg = "Simply translate these texts into Spanish. Each translation result has to start with ##. The sentences to be translated are" + original_texts
    # Create a dataset using GPT
    response = openai.ChatCompletion.create(model="gpt-3.5-turbo",
                                            messages=[{"role": "system", "content": system_msg},
                                            {"role": "user", "content": user_msg}])
    translated_text = response["choices"][0]["message"]["content"]

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
            [(img_width*anchor_x, img_height*anchor_y), ((img_width*anchor_x + txt_width*img_width), (img_height*anchor_y + txt_height*img_height))], fill=(205, 200, 205)
        )


        # text management
        translated_txt = info['Text']
        translated_txt_len = len(translated_txt)

        # the text has to be smaller than the height and width of the box
        if (math.floor(txt_width*img_width/translated_txt_len*2.5) < math.floor(img_height*txt_height)):
            font_size = math.floor(txt_width*img_width/translated_txt_len*2.5)  # for some reason calculated font size doesnt match WITHOUT *2.5
        else:
            font_size = math.floor(img_height*txt_height)
            print("size got determined based on the height")

        # Custom font style and font size
        myFont = ImageFont.truetype('fonts/Helvetica.ttf',font_size)

        
        
        # Add Text to an image
        I1.text((img_width*anchor_x+(img_width*txt_width)/2, img_height*anchor_y+(img_height*txt_height)/2), translated_txt, font=myFont, fill=(0, 0, 0), anchor='mm')
    
    # Display edited image
    #img.show()
    
    # Save the edited image
    #img.save("images/lancs2.png")

    # Save the image to an in-memory file
    in_mem_file = io.BytesIO()
    img.save(in_mem_file, format=img.format)
    in_mem_file.seek(0)


    return in_mem_file


# sentence is a sentence to be splitted
# ratio is a list containing multiple floating point numbers, the sum is not necessarily 1.0 ex. ratios = [0.4, 0.3, 1.4]
def split_sentence_by_characters(sentence, char_ratios):
    # Calculate the total number of characters in the sentence
    total_chars = len(sentence)
    
    # Calculate the split indices based on the normalized char_ratios
    total_ratio = sum(char_ratios)
    normalized_ratios = [ratio / total_ratio for ratio in char_ratios]
    
    split_indices = []
    cumulative_ratio = 0
    for ratio in normalized_ratios[:-1]:
        split_index = int(total_chars * (cumulative_ratio + ratio))
        
        # Make sure not to split in the middle of a word
        while split_index < total_chars and not sentence[split_index].isspace():
            split_index += 1
        
        split_indices.append(split_index)
        cumulative_ratio += ratio
    
    # Create the parts by iterating through split_indices
    parts = [] # containing some splitted sentences as a list
    start_idx = 0
    for split_idx in split_indices:
        part = sentence[start_idx:split_idx]
        parts.append(part.strip())  # Remove leading/trailing spaces
        start_idx = split_idx
        print("the part is ")
        print(*parts)
    
    # Add the last part
    parts.append(sentence[start_idx:])
    print("the part is ")
    print(*parts)
    return parts





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

    print("the text_info_list is")
    print(*text_info_list)







    # use block relation analysis
    for index, info in enumerate(text_info_list):
        anchor_x = info['BoundingBox']['Left']
        anchor_y = info['BoundingBox']['Top']
        block_height = info['BoundingBox']['Height']
        text = info['Text']
        last = False
        if index+1 == len(text_info_list):
            last = True
        block_relation_checker(anchor_x, anchor_y, block_height, text, last)





    # format original texts
    original_texts = ''
    for index, info in enumerate(txt_line_storage):
        original_texts += (str(index+1) + ' ')
        original_texts += info[0]
        original_texts += '\n'
    
    print('the original texts are below')
    print(original_texts)








    # translate them
    translated_texts = translate_with_gpt(original_texts)
    print(translated_texts)

    sentences = translated_texts.split("\n##")





    # update txt_line_storage
    for index_outer, info in enumerate(txt_line_storage):
        for index_inner, sentence in enumerate(sentences):
            translated_text = sentence
            if (index_outer == index_inner):
                if (index_outer == 0):
                    translated_text = translated_text[2:]
                txt_line_storage[index_outer][0] = translated_text
    translated_txt_line_storage = txt_line_storage

    print(*translated_txt_line_storage) # contains translated texts and the number of LINEs


    text_info_list_index = 0
    translated_text_info_list = []

    #TODO allocate the translated texts into each LINE block
    current_line = 0
    for chunk in translated_txt_line_storage:
        translated_complete_txt = chunk[0]
        num_of_line = chunk[1]

        # Initialize a list to store the selected dictionaries(containing one relational block)
        selected_dicts = []

        line_ratios = []

        # Loop through the list and select dictionaries within the specified range
        for position in range(current_line, current_line+num_of_line):
            if 0 <= position < len(text_info_list):
                selected_dicts.append(text_info_list[position])

        # Access the 'Width' values of the selected dictionaries using a loop
        for selected_dict in selected_dicts:
            width = selected_dict['BoundingBox']['Width']
            line_ratios.append(width)
            print("Width:", width)


        current_line += num_of_line

        print("the selected dicts is")
        print(*selected_dicts)

        print("the line ratio is")
        print(*line_ratios)
    
        splitted_result = split_sentence_by_characters(translated_complete_txt, line_ratios)
        

        for splitted_text in splitted_result:
            line_info = {'Text': splitted_text, 'BoundingBox': text_info_list[text_info_list_index]['BoundingBox']}
            translated_text_info_list.append(line_info)
            text_info_list_index += 1

    
    print("the translated_text_info_list is")
    print(*translated_text_info_list)



#########################################################################################


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


##############################################################################################













##############################################################################################################
    """ for index, info in enumerate(text_info_list):
        original_text = info['Text']
        translated_text = translate_with_gpt(original_text)
        if translated_text == 'INCMP':
            # don't translate and combine with the next sentence, based on the anchor_x
            incomplete_sentence += original_text
            incomplete_sentence += ' '
            inc_data_list.append[original_text, info['BoundingBox']['Width']]
            inc_counter += 1
            if inc_counter >=2 :
                incomplete_sentence = inc_data_list[0][0] + ' ' + inc_data_list[1][0]
                translated_text = translate_with_gpt(incomplete_sentence)
                # split the text into 2 sentences = get the lengh of each original box (txt)
                #translated_words = translated_text.split()
                #word_count = len(translated_words)
                result_parts = split_sentence(translated_text, [0.2, 0.5])
                for i, part in enumerate(result_parts):
                    print(f"Part {i + 1}: {part}")

        else:
            text_info_list[index]['Text'] = translated_text
            incomplete_sentence = ''
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
 """