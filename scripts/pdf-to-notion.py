from pdf2image import convert_from_path
from notion_client import Client
import os
import shutil
import requests

PDF_PATH = "/path/to/document.pdf"
NOTION_TOKEN = "notion API key"
TEMPORARY_FOLDER = "temp_images"
PARENT_PAGE_ID = "notion parent page ID"
FREEIMAGE_ID = "freeimage API ID"

def upload_image_to_freeimage(image_path, api_key):
    """
    Uploads an image to FreeImage.host and returns the image URL.
    
    :param image_path: Path to the image on the local file system.
    :param api_key: Your FreeImage.host API key.
    :return: The URL of the uploaded image on FreeImage.host.
    """
    api_url = "https://freeimage.host/api/1/upload"
    
    # Prepare the payload with the API key and the image file
    payload = {
        'key': api_key,
        'action': 'upload'
    }
    files = {
        'source': open(image_path, 'rb')
    }
    
    # Make the request to FreeImage API
    response = requests.post(api_url, data=payload, files=files)
    
    # Check if the request was successful
    if response.status_code == 200:
        response_json = response.json()
        if response_json['status_code'] == 200:
            # Extract the image URL from the response
            image_url = response_json['image']['url']
            return image_url
        else:
            raise Exception(f"Upload failed: {response_json['status_txt']}")
    else:
        # Raise an exception if the upload failed
        raise Exception(f"Failed to upload image: {response.status_code}, {response.text}")

# Convert PDF to list of images (one per page)
def convert_pdf_to_images(pdf_path, output_folder, dpi=200):
    images = convert_from_path(pdf_path, dpi=dpi, output_folder=output_folder)
    image_files = []
    for i, image in enumerate(images):
        image_path = os.path.join(output_folder, f"page_{i + 1}.png")
        image.save(image_path, "PNG")
        image_files.append(image_path)
    return image_files

# Create a new Notion page to hold all the images
def create_notion_page(notion, parent_page_id, title):
    new_page = notion.pages.create(
        parent={"page_id": parent_page_id},
        properties={
            "title": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            }
        },
    )
    return new_page['id']

# Add an external image to an existing Notion page as a block
def add_external_image_to_notion_page(notion, page_id, image_url):
    notion.blocks.children.append(
        block_id=page_id,
        children=[
            {
                "object": "block",
                "type": "image",
                "image": {
                    "type": "external",
                    "external": {
                        "url": image_url
                    }
                }
            },
            # Add an empty text block for notes between pages
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": "Notes can be added here..."
                            }
                        }
                    ]
                }
            }
        ]
    )

# Main function to upload PDF images to freeimage and add to Notion
def upload_pdf_images_to_notion(pdf_path, notion_token, parent_page_id, freeimage_id, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Initialize Notion client
    notion = Client(auth=notion_token)
    
    # Convert PDF to images
    image_files = convert_pdf_to_images(pdf_path, output_folder)
    
    # Create a single Notion page where all images will be uploaded
    title = "Lecture Slides"
    page_id = create_notion_page(notion, parent_page_id, title)
    
    # Upload each image to Imgur and add to Notion
    for i, image_path in enumerate(image_files):
        image_name = os.path.basename(image_path)
        print(f"Uploading Page {i + 1}...")
        
        # Upload image to Imgur and get the URL
        imgur_url = upload_image_to_freeimage(image_path, freeimage_id)
        
        # Add the image (via external URL) and notes block to the same Notion page
        add_external_image_to_notion_page(notion, page_id, imgur_url)

        # Delete the image after uploading it
        try:
            os.remove(image_path)
            print(f"Deleted {image_path} from the local machine.")
        except OSError as e:
            print(f"Error deleting {image_path}: {e.strerror}")

    if os.path.exists(output_folder):
        shutil.rmtree(output_folder)
        print(f"Temporary folder {output_folder} deleted.")

if __name__ == '__main__':
    upload_pdf_images_to_notion(pdf_path = PDF_PATH, notion_token = NOTION_TOKEN, parent_page_id = PARENT_PAGE_ID, freeimage_id = FREEIMAGE_ID, output_folder = TEMPORARY_FOLDER)
