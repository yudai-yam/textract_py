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

import deepl

# Import the openai package
import openai
import time

s3_client = boto3.client('s3')
textract_client = boto3.client('textract')
openai.api_key = constants.API_KEY


#current_block_info_storage = [] # store the current block info that are in the same chunk, this is used only in the block_relation_checker
#grouped_txt_info = [] # store the full text and its number of LINEs, this is used throughout the program


# identify text block
""" def block_relation_checker(anchor_x, anchor_y, block_height, text, last):
    global current_block_info_storage
    global grouped_txt_info

    text_block = []

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

            grouped_txt_info.append([combined_text, num_of_line])
            print("the text being appended is" + combined_text)
            # start from scratch
            current_block_info_storage = []

            if (last == True):
                grouped_txt_info.append([text, 1])
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

                grouped_txt_info.append([combined_text, num_of_line])


    print("the current block info storage is")
    print(*current_block_info_storage)
    print("the grouped_txt_info is")
    print(*grouped_txt_info)


    #TODO check if it's in the same parallel line
    
    # check if the y coordinate is the same (very close) as the previous one
    prev_anchor_y = current_block_info_storage[-1][1]
    if (-0.01 < prev_anchor_y - anchor_y < 0.01):
        print("recursive!")
        # if it's the same, save the previous records in stack (recursive?)
        #block_relation_checker(anchor_x, anchor_y, block_height, text, last)
     """
    


""" # identify text block
def block_relation_checker(text_info_list):
    current_block_info_storage = []
    global grouped_txt_info

    for index, info in enumerate(text_info_list):
        anchor_x = info['BoundingBox']['Left']
        anchor_y = info['BoundingBox']['Top']
        block_height = info['BoundingBox']['Height']
        text = info['Text']
        last = False
        if index + 1 == len(text_info_list):
            last = True

        print("the text being examined is " + text)


        

        if (current_block_info_storage == []):  # the very first line
            block_info = [anchor_x, anchor_y, block_height, text]
            current_block_info_storage.append(block_info)
            print("it's the very first sentence")

        else:  # not the very first line

            # TODO check if it's in the same parallel line
            # check if the y coordinate is the same (very close) as the previous one
            prev_anchor_y = current_block_info_storage[-1][1]
            if (-0.01 < prev_anchor_y - anchor_y < 0.01):
                print("recursive!")
                # if it's the same, save the previous records in stack (recursive?)
                block_relation_checker(text_info_list)
            
            

            # check the space in between two texts (blocks)
            print("this is not the first sentence")
            prev_anchor_y = current_block_info_storage[-1][1]
            prev_block_height = current_block_info_storage[-1][2]
            space = anchor_y - (prev_anchor_y + prev_block_height)  # represented by ratio against the original img size

            if (space > block_height):
                print("space>block")
                # belongs to another block
                # combine existing texts for translation
                combined_text = ' '.join(block_info[3] for block_info in current_block_info_storage)
                # store the number of LINE in a single block
                num_of_line = len(current_block_info_storage)

                grouped_txt_info.append([combined_text, num_of_line])
                print("the text being appended is" + combined_text)
                # start from scratch
                current_block_info_storage = []

                if (last == True):
                    grouped_txt_info.append([text, 1])
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

                    grouped_txt_info.append([combined_text, num_of_line])

        print("the current block info storage is")
        print(*current_block_info_storage)
        print("the grouped_txt_info is")
        print(*grouped_txt_info)
 """


def block_relation_checker(text_info_list): #You need width, height, x, y for each LINE
    current_block_info_storage = [] # 3D list [x, y, width, height, text, the number of consisted lines]
    # global grouped_txt_info

    for index, info in enumerate(text_info_list):
        anchor_x = info['BoundingBox']['Left']
        anchor_y = info['BoundingBox']['Top']
        block_height = info['BoundingBox']['Height']
        block_width = info['BoundingBox']['Width']
        text = info['Text']

        print("the text being examined is " + text)


        # check if there's similar x
        if (current_block_info_storage == []):  # the very first line
            block_info = [[anchor_x], [anchor_y], [block_width], [block_height], text, 1]
            current_block_info_storage.append(block_info)
            print("it's the very first sentence")

        else:  # not the very first line

            # TODO check if it's in the same parallel line
            # check if the y coordinate is the same (very close) as the previous one
            for index, each_info in enumerate(current_block_info_storage):
                prev_anchor_x = each_info[0][-1]
                prev_anchor_y = each_info[1][-1]
                prev_block_width = each_info[2][-1]
                prev_block_height = each_info[3][-1]

                prev_center_x = prev_anchor_x + prev_block_width/2
                center_x = anchor_x + block_width/2



                if (-0.01 < prev_anchor_x - anchor_x < 0.01) or (-0.01 < prev_center_x - center_x < 0.01):
                    print("same vertical line or the center of the text is very close")
            
                    # check the space in between two texts (blocks)
                    space = anchor_y - (prev_anchor_y + prev_block_height)  # represented by ratio against the original img size

                    """  if (space > block_height):
                        print("space>block")
                        # belongs to another block

                        block_info = [anchor_x, anchor_y, block_height, text, 1]
                        current_block_info_storage.append(block_info)
                        break """

                    if (space <= block_height):
                        print('very small space, likely to be in the group')
                        print("the text to be combined with is"+current_block_info_storage[index][4])
                        print(anchor_y)
                        current_block_info_storage[index][0].append(anchor_x)
                        current_block_info_storage[index][1].append(anchor_y)
                        current_block_info_storage[index][2].append(block_width)
                        current_block_info_storage[index][3].append(block_height)
                        text = ' '+ text
                        current_block_info_storage[index][4] += text
                        current_block_info_storage[index][5] += 1
                        break

                if (index+1 == len(current_block_info_storage)):
                #if (-0.01 < prev_anchor_y - anchor_y < 0.01):
                    #print("same horizontal line") 
                    print("could not find any group")
                    block_info = [[anchor_x], [anchor_y], [block_width], [block_height], text, 1]
                    current_block_info_storage.append(block_info)
                    break
                

        print("the current block info storage is")
        print(*current_block_info_storage)
       # print("the grouped_txt_info is")
        #print(*grouped_txt_info)
    return current_block_info_storage




def translate_with_gpt(original_texts):
    # Define the system message
    system_msg = 'You are a helpful tranlator.'

    # Define the user message
    #user_msg = f'''Simply translate this text into Spainsh. The text is: '
                #+ {original_text}
                #+ '.\nIf this text is incomplete, just return "INCMP" instead of translating. Note that just a noun is considered complete, even without an article.'''
    
    user_msg = """Simply translate these texts into English. 
                If you cannot translate, just print the original text, don't just skip it. 
                The number of line needs to match the prompt I give you.
                The sentences to be translated are""" + original_texts
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
            [(img_width*anchor_x, img_height*anchor_y), ((img_width*anchor_x + txt_width*img_width), (img_height*anchor_y + txt_height*img_height))], fill=(255, 255, 255)
        )


        # text management
        translated_txt = info['Text']
        translated_txt_len = len(translated_txt)

        # the text has to be smaller than the height and width of the box
        if (math.floor(txt_width*img_width/translated_txt_len*2 ) < math.floor(img_height*txt_height)):
            font_size = math.floor(txt_width*img_width/translated_txt_len*2)  # for some reason calculated font size doesnt match WITHOUT *2.5
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
    grouped_txt_info = block_relation_checker(text_info_list) # contains each geo info and translated texts





    # format original texts
    original_texts = ''
    for info in grouped_txt_info:
        original_texts += ' '
        original_texts += info[4]
        original_texts += '\n'
    
    print('the original texts are below')
    print(original_texts)






    start_time = time.time()
    # translate them
    translated_texts = translate_with_gpt(original_texts)
    end_time = time.time()
    print(translated_texts)
    print("the time it took to translate all is" + str(end_time-start_time))

    sentences = translated_texts.split("\n")
    sentences[0] = sentences[0][2:] # remove the first '##'



    # update grouped_txt_info
    for index_outer, info in enumerate(grouped_txt_info):
        grouped_txt_info[index_outer][4] = sentences[index_outer]

    print("this one below should be a text line storage (translated)")
    print(*grouped_txt_info) # contains each geo info and translated texts










    text_info_list_index = 0
    translated_text_info_list = []
     
    current_line = 0
    for chunk in grouped_txt_info:
        translated_txt = chunk[4]
        #num_of_line = chunk[5]

        line_ratios = []


        for width in chunk[2]:
            line_ratios.append(width)

        """  # Loop through the list and select dictionaries within the specified range
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
        print(*selected_dicts) """

        print("the line ratio is")
        print(*line_ratios)
    
        splitted_result = split_sentence_by_characters(translated_txt, line_ratios)
        
        print("splitted result is")
        print(*splitted_result)
        for index, splitted_text in enumerate(splitted_result):  # 3D list [x, y, width, height, text, the number of consisted lines]

            BoudningBoxDict = {
                'Width': chunk[2][index],
                'Height': chunk[3][index],
                'Left': chunk[0][index],
                'Top': chunk[1][index]
            }


            line_info = {'Text': splitted_text, 'BoundingBox': BoudningBoxDict}
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