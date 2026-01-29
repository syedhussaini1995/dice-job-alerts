# job_scraper_utils.py

import requests
from bs4 import BeautifulSoup
import time

def extract_job_description(job_link):
    """
    Visits the job link and extracts the full job description text.
    
    Args:
        job_link (str): The URL of the job posting.
        
    Returns:
        str: The cleaned job description text or a fallback message.
    """
    try:
        # Use requests to fetch the job detail page (we don't need Selenium here)
        response = requests.get(job_link, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        soup = BeautifulSoup(response.text, "html.parser")

        # Dice.com often puts the job description in a specific div/section.
        # This selector targets the main description area on a typical Dice job page.
        # Look for a div with the data-testid 'job-description-section' 
        # or the 'job-description' id, or similar.
        description_section = soup.find(class="job-detail-description-module__EJDWFq__jobDescription")

        # If the main section is found, extract the text content
        if description_section:
            # Get the text, stripping excessive whitespace and joining lines with a newline
            description_text = description_section.get_text(separator="\n", strip=True)
            return description_text
        else:
            return "Job Description section not found on the page."

    except requests.exceptions.RequestException as e:
        return f"Could not retrieve job description. Request error: {e}"
    except Exception as e:
        return f"An unexpected error occurred during description extraction: {e}"

# Example of how to use this (optional, for testing):
# if __name__ == '__main__':
#     # Use a known Dice job link for testing
#     test_link = "A_VALID_DICE_JOB_LINK_HERE" 
#     description = extract_job_description(test_link)
#     print(description)
