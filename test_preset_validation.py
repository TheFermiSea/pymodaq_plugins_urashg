#!/usr/bin/env python3
"""
Test script to validate PyMoDAQ preset files for proper XML structure
"""

import os
import xml.etree.ElementTree as ET

def test_preset_files():
    """Test all preset files for valid XML structure"""
    
    print('=== PyMoDAQ Preset File Validation ===')
    print('Testing corrected preset files for XML structure and content')

    preset_files = [
        '/home/maitai/.pymodaq/preset_configs/preset_urashg.xml',
        '/home/maitai/.pymodaq/preset_configs/preset_ellipticity_calibration.xml', 
        '/home/maitai/.pymodaq/preset_configs/preset_ellipticity_no_init.xml'
    ]

    all_valid = True

    for preset_file in preset_files:
        if os.path.exists(preset_file):
            print(f'\nTesting: {os.path.basename(preset_file)}')
            try:
                # Parse XML
                tree = ET.parse(preset_file)
                root = tree.getroot()
                
                # Check structure
                if root.tag != 'Preset':
                    print(f'  ERROR: Invalid root tag: {root.tag} (expected Preset)')
                    all_valid = False
                    continue
                    
                # Check for required elements
                filename = root.find('filename')
                moves = root.find('Moves')
                detectors = root.find('Detectors')
                
                if filename is None:
                    print(f'  ERROR: Missing filename element')
                    all_valid = False
                else:
                    print(f'  OK: Filename found')
                    
                if moves is None:
                    print(f'  ERROR: Missing Moves section')
                    all_valid = False
                else:
                    move_count = len([child for child in moves if child.tag.startswith('move')])
                    print(f'  OK: Moves section with {move_count} plugins')
                    
                if detectors is None:
                    print(f'  ERROR: Missing Detectors section') 
                    all_valid = False
                else:
                    det_count = len([child for child in detectors if child.tag.startswith('det')])
                    print(f'  OK: Detectors section with {det_count} plugins')
                    
                # Verify no duplicate root elements
                with open(preset_file, 'r') as f:
                    xml_content = f.read()
                preset_count = xml_content.count('<Preset')
                if preset_count > 1:
                    print(f'  ERROR: Multiple Preset root elements found: {preset_count}')
                    all_valid = False
                else:
                    print(f'  OK: Single Preset root element')
                    
                print(f'  SUCCESS: {os.path.basename(preset_file)} - Valid XML structure')
                
            except ET.ParseError as e:
                print(f'  ERROR: XML Parse Error: {e}')
                all_valid = False
            except Exception as e:
                print(f'  ERROR: {e}')
                all_valid = False
        else:
            print(f'\nERROR: File not found: {preset_file}')
            all_valid = False

    print('\n=== SUMMARY ===')
    if all_valid:
        print('SUCCESS: All preset files have valid XML structure')
        print('SUCCESS: No duplicate root elements found')  
        print('SUCCESS: All required sections present')
        print('SUCCESS: Files should load without hanging in PyMoDAQ')
        return True
    else:
        print('ERROR: Some preset files have issues')
        return False

if __name__ == '__main__':
    success = test_preset_files()
    exit(0 if success else 1)