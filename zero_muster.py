import requests
import json
import statistics
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import anthropic
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("nregs_zero_muster.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def get_zero_muster_data(date, district=None):
    """
    Fetch zero muster data from the NREGS MP dashboard API
    
    Args:
        date (str): Date in YYYY-MM-DD format
        district (str, optional): District name if specific district data is needed
    
    Returns:
        dict: API response data
    """
    base_url = "https://dashboard.nregsmp.org/api/employment_workers/zero-muster"
    
    if district:
        url = f"{base_url}?date={date}&district={district}"
    else:
        url = f"{base_url}?date={date}"
    
    logger.info(f"Fetching zero muster data from: {url}")
    response = requests.get(url)
    
    if response.status_code == 200:
        logger.info(f"Successfully fetched zero muster data from: {url}")
        return response.json()
    else:
        logger.error(f"Failed to fetch zero muster data: {response.status_code}")
        return None

def process_state_zero_muster_data(data):
    """
    Process state-level zero muster data to extract top/bottom districts and state averages
    
    Args:
        data (dict): State-level NREGS zero muster data
    
    Returns:
        dict: Processed data with top/bottom districts and state averages
    """
    if not data or 'results' not in data:
        logger.error("Invalid state zero muster data format")
        return None
    
    logger.info(f"Processing state zero muster data with {len(data['results'])} districts")
    
    # Format all data points to have 2 decimal places
    for district in data['results']:
        for key, value in district.items():
            if isinstance(value, float):
                district[key] = round(value, 2)
    
    # Sort districts by zero attendance percentage (lowest to highest, since lower is better)
    sorted_districts = sorted(data['results'], key=lambda x: x.get('zero_attendance_percentage', 100))
    
    # Add rank to each district
    district_ranks = {}
    for i, district in enumerate(sorted_districts):
        district_ranks[district['group_name']] = i + 1
    
    # Extract top 1 and bottom 1 districts
    top_district = sorted_districts[0]  # Best district has lowest zero attendance percentage
    bottom_district = sorted_districts[-1]  # Worst district has highest zero attendance percentage
    
    # Calculate state averages for key metrics
    avg_total_muster_issued = round(statistics.mean([d.get('total_muster_issued', 0) for d in data['results']]), 2)
    avg_total_zero_attendance = round(statistics.mean([d.get('total_zero_attendance', 0) for d in data['results']]), 2)
    avg_zero_attendance_percentage = round(statistics.mean([d.get('zero_attendance_percentage', 0) for d in data['results']]), 2)
    avg_zero_muster_marks = round(statistics.mean([d.get('zero_muster_marks', 0) for d in data['results']]), 2)
    
    logger.info(f"Top district: {top_district['group_name']} with zero attendance percentage {top_district.get('zero_attendance_percentage', 0)}%")
    logger.info(f"Bottom district: {bottom_district['group_name']} with zero attendance percentage {bottom_district.get('zero_attendance_percentage', 0)}%")
    logger.info(f"State average zero attendance percentage: {avg_zero_attendance_percentage}%")
    logger.info(f"State average zero muster marks: {avg_zero_muster_marks}")
    
    return {
        "top_district": top_district,
        "bottom_district": bottom_district,
        "state_averages": {
            "total_muster_issued": avg_total_muster_issued,
            "total_zero_attendance": avg_total_zero_attendance,
            "zero_attendance_percentage": avg_zero_attendance_percentage,
            "zero_muster_marks": avg_zero_muster_marks
        },
        "district_ranks": district_ranks,
        "total_districts": len(sorted_districts)
    }

def process_district_zero_muster_data(data):
    """
    Process district-level zero muster data to summarize block information
    
    Args:
        data (dict): District-level NREGS zero muster data
    
    Returns:
        dict: Processed data with block information and district summary
    """
    if not data or 'results' not in data:
        logger.error("Invalid district zero muster data format")
        return None
    
    logger.info(f"Processing district zero muster data with {len(data['results'])} blocks")
    
    # Format all data points to have 2 decimal places
    for block in data['results']:
        for key, value in block.items():
            if isinstance(value, float):
                block[key] = round(value, 2)
    
    # Sort blocks by zero attendance percentage (lowest to highest, since lower is better)
    sorted_blocks = sorted(data['results'], key=lambda x: x.get('zero_attendance_percentage', 100))
    
    # Calculate district averages
    avg_total_muster_issued = round(statistics.mean([b.get('total_muster_issued', 0) for b in data['results']]), 2)
    avg_total_zero_attendance = round(statistics.mean([b.get('total_zero_attendance', 0) for b in data['results']]), 2)
    avg_zero_attendance_percentage = round(statistics.mean([b.get('zero_attendance_percentage', 0) for b in data['results']]), 2)
    avg_zero_muster_marks = round(statistics.mean([b.get('zero_muster_marks', 0) for b in data['results']]), 2)
    
    # Get highest and lowest performing blocks
    best_block = sorted_blocks[0] if sorted_blocks else None
    worst_block = sorted_blocks[-1] if sorted_blocks else None
    
    if best_block and worst_block:
        logger.info(f"Best performing block: {best_block['group_name']} with zero attendance percentage {best_block.get('zero_attendance_percentage', 0)}%")
        logger.info(f"Worst performing block: {worst_block['group_name']} with zero attendance percentage {worst_block.get('zero_attendance_percentage', 0)}%")
        logger.info(f"District average zero attendance percentage: {avg_zero_attendance_percentage}%")
        logger.info(f"District average zero muster marks: {avg_zero_muster_marks}")
    
    return {
        "blocks": sorted_blocks,
        "district_summary": {
            "total_blocks": len(data['results']),
            "average_total_muster_issued": avg_total_muster_issued,
            "average_total_zero_attendance": avg_total_zero_attendance,
            "average_zero_attendance_percentage": avg_zero_attendance_percentage,
            "average_zero_muster_marks": avg_zero_muster_marks,
            "best_performing_block": best_block['group_name'] if best_block else None,
            "best_zero_attendance_percentage": best_block.get('zero_attendance_percentage', 0) if best_block else 0,
            "worst_performing_block": worst_block['group_name'] if worst_block else None,
            "worst_zero_attendance_percentage": worst_block.get('zero_attendance_percentage', 0) if worst_block else 0
        }
    }

def generate_zero_muster_analysis(state_data, district_data, target_district):
    """
    Generate analysis report using Claude 3.7 with thinking mode
    
    Args:
        state_data (dict): Processed state data
        district_data (dict): Processed district data
        target_district (str): Name of the target district
    
    Returns:
        str: Analysis report
    """
    # Create prompt template
    prompt = """
You are an AI analyst tasked with evaluating the performance of districts and blocks in Madhya Pradesh, India,
based on the National Rural Employment Guarantee Act (NREGA) data. Your goal is to provide a concise, 
professional analysis of a target district's performance in relation to the state's top and bottom performers,
as well as an assessment of the blocks within the target district.

You will be provided with the following data:

<state_data>
{state_data}
</state_data>

<district_data>
{district_data}
</district_data>

The target district for analysis is:
<target_district>{target_district}</target_district>

Analyze the provided data and generate a brief, professional report that includes:

1. A comparison of the target district's performance to the state's top and bottom performers, highlighting strengths and weaknesses.
2. An evaluation of the blocks within the target district, identifying high-performing and underperforming blocks.

Your analysis should be precise, concise, and use professional language.
Focus on the zero muster metrics:

1. Total muster issued: Total number of muster rolls issued for work
2. Total zero attendance: Number of muster rolls with zero attendance
3. Zero attendance percentage: Percentage of musters with zero attendance
4. Zero muster marks: Marks awarded (lower zero attendance percentage is better)

Zero musters are discouraged as they indicate inefficiency in work allocation or supervision.

Present your analysis in the following format:

<analysis>
<district_performance>
[Provide a 2-3 sentence analysis of the target district's performance compared to the top and bottom districts in the state. Highlight the district's zero muster percentage and its implications.]
</district_performance>

<efficiency_analysis>
[Provide a 2-3 sentence analysis specifically about the relationship between total musters issued and zero attendance percentage in the district, and how it compares to state averages.]
</efficiency_analysis>

<block_performance>
[Provide a 2-3 sentence analysis of the blocks within the target district, identifying the best and worst performers in minimizing zero musters and any notable patterns.]
</block_performance>

<recommendations>
[Offer 1-2 concise, data-driven recommendations for reducing zero musters in the target district, particularly focusing on systemic improvements.]
</recommendations>
</analysis>

Ensure that your analysis is based solely on the provided data and focuses on the most significant insights that can be derived from the information given.
Your response should contain data to validate your points. give key insights of district,block and improvement potential. 
Include district ranking/score in the component, top districts, improvement potential and suggestions, blocks in the district who are performig good and bad. 
"""
    
    # Format the prompt with actual data
    formatted_prompt = prompt.format(
        state_data=json.dumps(state_data, indent=2),
        district_data=json.dumps(district_data, indent=2),
        target_district=target_district
    )
    
    # Log the prompt (optional, can be disabled for production)
    logger.debug(f"Prompt to Claude for zero muster analysis:\n{formatted_prompt}")
    
    # Call Claude 3.7 API with thinking mode
    return call_claude_api(formatted_prompt)

def call_claude_api(prompt):
    """
    Call Claude 3.7 API with thinking mode enabled
    
    Args:
        prompt (str): Prompt to send to Claude
    
    Returns:
        str: Claude's response
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        error_msg = "ANTHROPIC_API_KEY environment variable not set"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # Set model
    model = "claude-3-7-sonnet-20250219"
    logger.info(f"Using Claude model: {model} with thinking mode")
    
    try:
        client = anthropic.Anthropic(api_key=api_key)
        
        # Request creation with thinking mode
        response = client.messages.create(
            model=model,
            max_tokens=20000,
            thinking={
                "type": "enabled",
                "budget_tokens": 16000
            },
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Log token usage
        prompt_tokens = response.usage.input_tokens
        completion_tokens = response.usage.output_tokens
        total_tokens = prompt_tokens + completion_tokens
        
        logger.info(f"Token usage - Prompt: {prompt_tokens}, Completion: {completion_tokens}, Total: {total_tokens}")
        
        # Check and log thinking output
        thinking_output = None
        if hasattr(response, 'thinking') and response.thinking:
            thinking_text = response.thinking.thinking_text
            thinking_tokens = response.thinking.tokens
            logger.info(f"Thinking mode used: {thinking_tokens} tokens")
            
            # Create output directory if it doesn't exist
            os.makedirs("output", exist_ok=True)
            
            # Save thinking to file
            thinking_file = os.path.join("output", f"zero_muster_thinking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(thinking_file, 'w', encoding='utf-8') as f:
                f.write(thinking_text)
            logger.info(f"Thinking output saved to {thinking_file}")
            
            thinking_output = thinking_text
        else:
            logger.info("No thinking output received")
        
        # Extract the actual response text
        response_text = ""
        for content_block in response.content:
            if hasattr(content_block, 'text'):
                response_text += content_block.text
        
        # Create output directory if it doesn't exist
        os.makedirs("output", exist_ok=True)
        
        # Save full response to file
        response_file = os.path.join("output", f"zero_muster_claude_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(response_file, 'w', encoding='utf-8') as f:
            response_data = {
                "model": model,
                "response_text": response_text,
                "thinking_text": thinking_output,
                "token_usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "thinking_tokens": thinking_tokens if hasattr(response, 'thinking') and response.thinking else 0
                }
            }
            json.dump(response_data, f, indent=2)
        
        logger.info(f"Full response data saved to {response_file}")
        
        return response_text
    
    except Exception as e:
        logger.error(f"Error calling Claude API: {str(e)}")
        raise

def main(date=None, district=None, output_format="text"):
    """
    Main function to fetch and process NREGS zero muster data, then analyze it
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format
        district (str, optional): District name for specific data
        output_format (str, optional): Output format ('text' or 'json')
    
    Returns:
        Union[str, dict]: Analysis result in specified format
    """
    logger.info(f"Starting NREGS zero muster analysis for district: {district}, date: {date if date else 'current'}")
    
    # Use current date if none provided
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Using current date: {date}")
    
    # Get state-level data
    logger.info("Fetching state-level zero muster data")
    state_data = get_zero_muster_data(date)
    if not state_data:
        logger.error("Failed to get state-level zero muster data")
        return None
    
    processed_state_data = process_state_zero_muster_data(state_data)
    if not processed_state_data:
        logger.error("Failed to process state-level zero muster data")
        return None
    
    result = {
        "date": date,
        "state_data": {
            "top_district": processed_state_data["top_district"],
            "bottom_district": processed_state_data["bottom_district"],
            "state_averages": processed_state_data["state_averages"]
        }
    }
    
    # Check if district is provided
    if not district:
        error_msg = "District name is required for analysis"
        logger.error(error_msg)
        return error_msg
    
    # Get district-level data
    logger.info(f"Fetching zero muster data for district: {district}")
    district_data = get_zero_muster_data(date, district)
    if not district_data:
        logger.error(f"Failed to get zero muster data for district: {district}")
        return None
    
    processed_district_data = process_district_zero_muster_data(district_data)
    if not processed_district_data:
        logger.error(f"Failed to process zero muster data for district: {district}")
        return None
    
    # Get district rank
    district_rank = processed_state_data["district_ranks"].get(district, None)
    total_districts = processed_state_data["total_districts"]
    
    # Find the district data in the state data for complete information
    target_district_data = None
    for d in state_data['results']:
        if d['group_name'] == district:
            target_district_data = d
            break
    
    result["district_data"] = {
        "district_name": district,
        "state_rank": district_rank,
        "total_districts": total_districts,
        "district_info": target_district_data,
        "details": processed_district_data
    }
    
    # Generate analysis using Claude
    logger.info("Generating zero muster analysis using Claude 3.7")
    analysis = generate_zero_muster_analysis(
        result["state_data"], 
        result["district_data"], 
        district
    )
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Create output based on requested format
    if output_format == "json":
        result["analysis"] = analysis
        
        # Save output to file
        filename = os.path.join("output", f"nregs_zero_muster_analysis_{district.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        logger.info(f"Analysis saved to {filename}")
        
        return result
    else:
        # Save output to file
        filename = os.path.join("output", f"nregs_zero_muster_analysis_{district.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(analysis)
        logger.info(f"Analysis saved to {filename}")
        
        return analysis

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NREGS Zero Muster Data Analysis')
    parser.add_argument('--date', type=str, help='Date in YYYY-MM-DD format')
    parser.add_argument('--district', type=str, required=True, help='District name')
    parser.add_argument('--output', type=str, default="text", choices=["text", "json"],
                        help='Output format (text or json)')
    
    args = parser.parse_args()
    
    try:
        result = main(args.date, args.district, args.output)
        
        if args.output == "json":
            print(json.dumps(result, indent=4))
        else:
            print(result)
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        print(f"Error: {str(e)}")