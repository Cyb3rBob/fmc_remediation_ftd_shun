#!/usr/bin/env python
"""
Cisco Firepower Management Center (FMC) Remediation module - Shun
"""

import sys
import xml.etree.ElementTree as ET
from ftd_connector import ftd_connection

param_1 = sys.argv[1]
param_2 = sys.argv[2]

# Read Firewall Details from instance.conf
tree = ET.parse("instance.conf")
firewall_ip = tree.find("./config/string[@name='firewall_ip']").text
firewall_username = tree.find("./config/string[@name='firewall_username']").text
firewall_password = tree.find("./config/string[@name='firewall_password']").text
firewall_port = tree.find("./config/string[@name='firewall_port']").text

try:
    # Connect and send shun command using ftd_connector
    with ftd_connection(
        ip=firewall_ip,
        username=firewall_username,
        password=firewall_password
    ) as ftd:
        output = ftd.send_command_clish("shun " + param_2)
        print("\nShun output:")
        print(output)

except Exception as e:
    print(f"An error occurred: {e}")
