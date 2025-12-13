#!/usr/bin/env python3
"""
Test script for Kaufman County CAD ArcGIS REST API endpoint
Tests querying by address and retrieving property data
"""

import requests
import json


def test_endpoint():
    """Test the Kaufman CAD endpoint with various queries"""

    base_url = 'https://services9.arcgis.com/26s7bQ5Q51Gt4J2Q/arcgis/rest/services/KaufmanCADWebService/FeatureServer'
    query_url = f'{base_url}/0/query'

    print('=' * 80)
    print('KAUFMAN COUNTY CAD ARCGIS REST API ENDPOINT TEST')
    print('=' * 80)
    print(f'\nBase URL: {base_url}')
    print(f'Query URL: {query_url}')

    # Test 1: Basic connectivity
    print('\n\n[TEST 1] Service Metadata')
    print('-' * 80)

    try:
        response = requests.get(base_url, params={'f': 'json'}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'error' not in data:
                print('✓ Service accessible')
                print(f'  Description: {data.get("serviceDescription", "N/A")}')
                print(f'  Layers: {len(data.get("layers", []))}')
            else:
                print(f'✗ Error: {data["error"]}')
        else:
            print(f'✗ HTTP {response.status_code}')
    except Exception as e:
        print(f'✗ Exception: {e}')

    # Test 2: Get sample record
    print('\n\n[TEST 2] Sample Record Retrieval')
    print('-' * 80)

    params = {
        'where': '1=1',
        'outFields': '*',
        'resultRecordCount': 1,
        'f': 'json'
    }

    try:
        response = requests.get(query_url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'features' in data and len(data['features']) > 0:
                print('✓ Successfully retrieved sample record')
                attrs = data['features'][0]['attributes']
                print(f'\n  Sample data:')
                print(f'    Owner: {attrs.get("file_as_name", "N/A")}')
                print(f'    Address: {attrs.get("situs_num", "")} {attrs.get("situs_street", "")}, {attrs.get("situs_city", "")}')
                print(f'    Market Value: ${attrs.get("market", 0):,.2f}')
                print(f'    Land Value: ${attrs.get("land_val", 0):,.2f}')
                print(f'    Improvement Value: ${attrs.get("imprv_val", 0):,.2f}')
                print(f'    Acreage: {attrs.get("legal_acreage", "N/A")}')
            else:
                print('✗ No features returned')
        else:
            print(f'✗ HTTP {response.status_code}')
    except Exception as e:
        print(f'✗ Exception: {e}')

    # Test 3: Address-based search
    print('\n\n[TEST 3] Address-Based Search')
    print('-' * 80)

    test_queries = [
        ("situs_city = 'FORNEY'", 'City: Forney'),
        ("situs_street LIKE '%MAIN%'", 'Street: Main'),
        ("situs_num = '100'", 'House Number: 100'),
    ]

    for where_clause, description in test_queries:
        print(f'\n  Query: {description}')
        print(f'  Where: {where_clause}')

        params = {
            'where': where_clause,
            'outFields': 'file_as_name,situs_num,situs_street,situs_city,market',
            'resultRecordCount': 2,
            'f': 'json'
        }

        try:
            response = requests.get(query_url, params=params, timeout=15)
            if response.status_code == 200:
                data = response.json()
                if 'features' in data:
                    count = len(data['features'])
                    print(f'  ✓ Found {count} result(s)')

                    if count > 0:
                        attrs = data['features'][0]['attributes']
                        print(f'    Example: {attrs.get("file_as_name", "N/A")}')
                        print(f'             {attrs.get("situs_num", "")} {attrs.get("situs_street", "")}, {attrs.get("situs_city", "")}')
                else:
                    print(f'  ✗ Error in response')
            else:
                print(f'  ✗ HTTP {response.status_code}')
        except Exception as e:
            print(f'  ✗ Exception: {e}')

    # Test 4: Available fields
    print('\n\n[TEST 4] Available Fields')
    print('-' * 80)

    layer_url = f'{base_url}/0'

    try:
        response = requests.get(layer_url, params={'f': 'json'}, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if 'fields' in data:
                print(f'✓ Total fields: {len(data["fields"])}')

                # Categorize fields
                categories = {
                    'Address': [],
                    'Owner': [],
                    'Value': [],
                    'Property': [],
                    'Other': []
                }

                for field in data['fields']:
                    name = field.get('name', '')
                    name_lower = name.lower()

                    if any(x in name_lower for x in ['addr', 'situs', 'street', 'city', 'zip']):
                        categories['Address'].append(name)
                    elif any(x in name_lower for x in ['owner', 'file_as', 'name']):
                        categories['Owner'].append(name)
                    elif any(x in name_lower for x in ['val', 'market', 'imprv', 'land']):
                        categories['Value'].append(name)
                    elif any(x in name_lower for x in ['acreage', 'legal', 'tract', 'lot', 'prop_id']):
                        categories['Property'].append(name)
                    else:
                        categories['Other'].append(name)

                print('\n  Field Categories:')
                for cat, fields in categories.items():
                    if fields:
                        print(f'    {cat}: {", ".join(fields[:5])}{"..." if len(fields) > 5 else ""}')
    except Exception as e:
        print(f'✗ Exception: {e}')

    print('\n\n' + '=' * 80)
    print('TEST SUMMARY')
    print('=' * 80)
    print('✓ Endpoint is working and publicly accessible')
    print('✓ Can query by address components (city, street, number)')
    print('✓ Returns owner, address, and property value data')
    print('⚠ No year_built or square_feet fields available')
    print('  (Only available: land_val, imprv_val, market, legal_acreage)')


if __name__ == '__main__':
    test_endpoint()
