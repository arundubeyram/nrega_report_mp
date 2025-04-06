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
        logging.FileHandler("nregs_inspection.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

def get_inspection_data(date, district=None):
    """
    Fetch area officer inspection data from the NREGS MP dashboard API
    
    Args:
        date (str): Date in YYYY-MM-DD format
        district (str, optional): District name if specific district data is needed
    
    Returns:
        dict: API response data
    """
    base_url = "https://dashboard.nregsmp.org/api/employment_workers/inspection"
    
    if district:
        url = f"{base_url}?date={date}&district={district}"
    else:
        url = f"{base_url}?date={date}"
    
    logger.info(f"Fetching inspection data from: {url}")
    response = requests.get(url)
    
    if response.status_code == 200:
        logger.info(f"Successfully fetched inspection data from: {url}")
        return response.json()
    else:
        logger.error(f"Failed to fetch inspection data: {response.status_code}")
        return None

def process_state_inspection_data(data):
    """
    Process state-level inspection data to extract top/bottom districts and state averages
    
    Args:
        data (dict): State-level NREGS inspection data
    
    Returns:
        dict: Processed data with top/bottom districts and state averages
    """
    if not data or 'results' not in data:
        logger.error("Invalid state inspection data format")
        return None
    
    logger.info(f"Processing state inspection data with {len(data['results'])} districts")
    
    # Format all data points to have 2 decimal places
    for district in data['results']:
        for key, value in district.items():
            if isinstance(value, float):
                district[key] = round(value, 2)
    
    # Sort districts by total marks (highest to lowest)
    sorted_districts = sorted(data['results'], key=lambda x: x.get('total_visit_marks', 0), reverse=True)
    
    # If there are districts with equal marks, sort them by total visits
    for i in range(len(sorted_districts) - 1):
        if sorted_districts[i]['total_visit_marks'] == sorted_districts[i+1]['total_visit_marks']:
            total_visits_i = sorted_districts[i]['dpc_ws_visited'] + sorted_districts[i]['adpc_ws_visited']
            total_visits_i_plus_1 = sorted_districts[i+1]['dpc_ws_visited'] + sorted_districts[i+1]['adpc_ws_visited']
            
            if total_visits_i < total_visits_i_plus_1:
                sorted_districts[i], sorted_districts[i+1] = sorted_districts[i+1], sorted_districts[i]
    
    # Add rank to each district
    district_ranks = {}
    for i, district in enumerate(sorted_districts):
        district_ranks[district['group_name']] = i + 1
    
    # Extract top 1 and bottom 1 districts
    top_district = sorted_districts[0]
    bottom_district = sorted_districts[-1]
    
    # Calculate state averages for key metrics
    avg_dpc_ws_visited = round(statistics.mean([d.get('dpc_ws_visited', 0) for d in data['results']]), 2)
    avg_adpc_ws_visited = round(statistics.mean([d.get('adpc_ws_visited', 0) for d in data['results']]), 2)
    avg_dpc_marks = round(statistics.mean([d.get('dpc_marks', 0) for d in data['results']]), 2)
    avg_adpc_marks = round(statistics.mean([d.get('adpc_marks', 0) for d in data['results']]), 2)
    avg_total_marks = round(statistics.mean([d.get('total_visit_marks', 0) for d in data['results']]), 2)
    
    logger.info(f"Top district: {top_district['group_name']} with total marks {top_district.get('total_visit_marks', 0)}")
    logger.info(f"Bottom district: {bottom_district['group_name']} with total marks {bottom_district.get('total_visit_marks', 0)}")
    logger.info(f"State average total marks: {avg_total_marks}")
    
    # Include date range information
    range_start = data.get('range_start', '')
    range_end = data.get('range_end', '')
    
    return {
        "top_district": top_district,
        "bottom_district": bottom_district,
        "state_averages": {
            "dpc_ws_visited": avg_dpc_ws_visited,
            "adpc_ws_visited": avg_adpc_ws_visited,
            "dpc_marks": avg_dpc_marks,
            "adpc_marks": avg_adpc_marks,
            "total_marks": avg_total_marks
        },
        "district_ranks": district_ranks,
        "total_districts": len(sorted_districts),
        "date_range": {
            "start": range_start,
            "end": range_end
        }
    }

def process_district_inspection_data(data):
    """
    Process district-level inspection data to summarize block information
    
    Args:
        data (dict): District-level NREGS inspection data
    
    Returns:
        dict: Processed data with block information and district summary
    """
    if not data or 'results' not in data:
        logger.error("Invalid district inspection data format")
        return None
    
    logger.info(f"Processing district inspection data with {len(data['results'])} blocks")
    
    # Format all data points to have 2 decimal places
    for block in data['results']:
        for key, value in block.items():
            if isinstance(value, float):
                block[key] = round(value, 2)
    
    # Sort blocks by total marks (highest to lowest)
    sorted_blocks = sorted(data['results'], key=lambda x: x.get('total_visit_marks', 0), reverse=True)
    
    # If there are blocks with equal marks, sort them by total visits
    for i in range(len(sorted_blocks) - 1):
        if sorted_blocks[i]['total_visit_marks'] == sorted_blocks[i+1]['total_visit_marks']:
            total_visits_i = sorted_blocks[i]['dpc_ws_visited'] + sorted_blocks[i]['adpc_ws_visited']
            total_visits_i_plus_1 = sorted_blocks[i+1]['dpc_ws_visited'] + sorted_blocks[i+1]['adpc_ws_visited']
            
            if total_visits_i < total_visits_i_plus_1:
                sorted_blocks[i], sorted_blocks[i+1] = sorted_blocks[i+1], sorted_blocks[i]
    
    # Calculate district averages
    avg_dpc_ws_visited = round(statistics.mean([b.get('dpc_ws_visited', 0) for b in data['results']]), 2)
    avg_adpc_ws_visited = round(statistics.mean([b.get('adpc_ws_visited', 0) for b in data['results']]), 2)
    avg_dpc_marks = round(statistics.mean([b.get('dpc_marks', 0) for b in data['results']]), 2)
    avg_adpc_marks = round(statistics.mean([b.get('adpc_marks', 0) for b in data['results']]), 2)
    avg_total_marks = round(statistics.mean([b.get('total_visit_marks', 0) for b in data['results']]), 2)
    
    # Get highest and lowest performing blocks
    highest_block = sorted_blocks[0] if sorted_blocks else None
    lowest_block = sorted_blocks[-1] if sorted_blocks else None
    
    if highest_block and lowest_block:
        logger.info(f"Highest performing block: {highest_block['group_name']} with total marks {highest_block.get('total_visit_marks', 0)}")
        logger.info(f"Lowest performing block: {lowest_block['group_name']} with total marks {lowest_block.get('total_visit_marks', 0)}")
        logger.info(f"District average total marks: {avg_total_marks}")
    
    # Include date range information
    range_start = data.get('range_start', '')
    range_end = data.get('range_end', '')
    
    return {
        "blocks": sorted_blocks,
        "district_summary": {
            "total_blocks": len(data['results']),
            "average_dpc_ws_visited": avg_dpc_ws_visited,
            "average_adpc_ws_visited": avg_adpc_ws_visited,
            "average_dpc_marks": avg_dpc_marks,
            "average_adpc_marks": avg_adpc_marks,
            "average_total_marks": avg_total_marks,
            "highest_performing_block": highest_block['group_name'] if highest_block else None,
            "highest_total_marks": highest_block.get('total_visit_marks', 0) if highest_block else 0,
            "lowest_performing_block": lowest_block['group_name'] if lowest_block else None,
            "lowest_total_marks": lowest_block.get('total_visit_marks', 0) if lowest_block else 0,
            "date_range": {
                "start": range_start,
                "end": range_end
            }
        }
    }

def generate_inspection_analysis(state_data, district_data, target_district):
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
Focus on the area officer inspection metrics:

1. DPC (District Program Coordinator) who is District zcollector worksite visits
2. ADPC (Additional District Program Coordinator) who is CEO ZP worksite visits
3. Total marks awarded for these visits (maximum 6 marks)

The data represents area officer app-based monthly inspection reports.

Present your analysis in the following format:

<analysis>
<district_performance>
[Provide a 2-3 sentence analysis of the target district's performance compared to the top and bottom districts in the state. Highlight key strengths and weaknesses in inspection activities.]
</district_performance>

<officer_inspection>
[Provide a 1-2 sentence analysis specifically about the district's performance in both DPC and ADPC inspection activities. Note which officer type is more active in the district.]
</officer_inspection>

<block_performance>
[Provide a 1-2 sentence analysis of the blocks within the target district, identifying the highest and lowest performers and any notable trends in inspection activities.]
</block_performance>

<recommendations>
[Offer 1-2 concise, data-driven recommendations for improving the target district's inspection activities, particularly focusing on officer types that may be underperforming.]
</recommendations>
</analysis>

Ensure that your analysis is based solely on the provided data and focuses on the most significant insights that can be derived from the information given.Your response should
contain data to validate your points, Note that there is only 1 DPC and ADPC in whole district, and only see there District level visit when analysing.
Include district ranking/score in the component, top districts, improvement potential and suggestions, blocks in the district who are performig good and bad. 
"""
    
    # Format the prompt with actual data
    formatted_prompt = prompt.format(
        state_data=json.dumps(state_data, indent=2),
        district_data=json.dumps(district_data, indent=2),
        target_district=target_district
    )
    
    # Log the prompt (optional, can be disabled for production)
    logger.debug(f"Prompt to Claude for inspection analysis:\n{formatted_prompt}")
    
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
            
            # Save thinking to file
            thinking_file = f"inspection_thinking_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
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
        
        # Save full response to file
        response_file = f"inspection_claude_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
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
    Main function to fetch and process NREGS inspection data, then analyze it
    
    Args:
        date (str, optional): Date in YYYY-MM-DD format
        district (str, optional): District name for specific data
        output_format (str, optional): Output format ('text' or 'json')
    
    Returns:
        Union[str, dict]: Analysis result in specified format
    """
    logger.info(f"Starting NREGS inspection analysis for district: {district}, date: {date if date else 'current'}")
    
    # Use current date if none provided
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")
        logger.info(f"Using current date: {date}")
    
    # Get state-level data
    logger.info("Fetching state-level inspection data")
    state_data = get_inspection_data(date)
    if not state_data:
        logger.error("Failed to get state-level inspection data")
        return None
    
    processed_state_data = process_state_inspection_data(state_data)
    if not processed_state_data:
        logger.error("Failed to process state-level inspection data")
        return None
    
    result = {
        "date": date,
        "state_data": {
            "top_district": processed_state_data["top_district"],
            "bottom_district": processed_state_data["bottom_district"],
            "state_averages": processed_state_data["state_averages"],
            "date_range": processed_state_data["date_range"]
        }
    }
    
    # Check if district is provided
    if not district:
        error_msg = "District name is required for analysis"
        logger.error(error_msg)
        return error_msg
    
    # Get district-level data
    logger.info(f"Fetching inspection data for district: {district}")
    district_data = get_inspection_data(date, district)
    if not district_data:
        logger.error(f"Failed to get inspection data for district: {district}")
        return None
    
    processed_district_data = process_district_inspection_data(district_data)
    if not processed_district_data:
        logger.error(f"Failed to process inspection data for district: {district}")
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
    logger.info("Generating inspection analysis using Claude 3.7")
    analysis = generate_inspection_analysis(
        result["state_data"], 
        result["district_data"], 
        district
    )
    
    # Create output based on requested format
    if output_format == "json":
        result["analysis"] = analysis
        
        # Save output to file
        filename = f"nregs_inspection_analysis_{district.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=4)
        logger.info(f"Analysis saved to {filename}")
        
        return result
    else:
        # Save output to file
        filename = f"nregs_inspection_analysis_{district.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(analysis)
        logger.info(f"Analysis saved to {filename}")
        
        return analysis

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='NREGS Area Officer Inspection Data Analysis')
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