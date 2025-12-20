#!/usr/bin/env python3
"""
Parse Grapevine PDF permit data and convert to JSON format.
The PDF was manually downloaded from MyGov Grapevine portal.
"""

import json
import re
from datetime import datetime
from pathlib import Path

# Raw permit data extracted from the PDF
# This is the structured data from the 50-page PDF report
GRAPEVINE_PERMITS = [
    {
        "permit_number": "25-003912",
        "permit_type": "Temporary Use Permit",
        "description": "Temporary Use Permit, Holiday Main Street Wine Tour, November 15, 2025, 11:00 a.m. to 4:30 p.m.",
        "address": "624 S Main St.",
        "date_started": "11/15/2025",
        "permit_issued": "10/09/2025",
        "valuation": 0,
        "sqft": 0,
        "contacts": "City Of Grapevine C & V Bureau, Giddens Gallery of Fine Art, Michele Wilson"
    },
    {
        "permit_number": "25-004223",
        "permit_type": "Building - Multi-Family Alteration",
        "description": "Repair exterior balconies at Units on the building centers",
        "address": "3900 Grapevine Mills Pkwy., 13",
        "date_started": "11/02/2025",
        "permit_issued": "11/21/2025",
        "valuation": 16800,
        "sqft": 1800,
        "contacts": "Camden Riverwalk Apartments, Shannon White, Hentana Construction - 4695818199 - swhite@hentanaconstruction.com"
    },
    {
        "permit_number": "25-004224",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Sewer repair by tunnel - up to 10'",
        "address": "925 Wildwood Cir.",
        "date_started": "11/03/2025",
        "permit_issued": "11/03/2025",
        "valuation": 12788,
        "sqft": 0,
        "contacts": "Jeff Sims, billyGO DFW, LLC - 8177226151 - dottie@billygo.com, Justin Baylis"
    },
    {
        "permit_number": "25-004225",
        "permit_type": "Building - Roofing",
        "description": "reroof",
        "address": "4209 Squire Ct.",
        "date_started": "11/03/2025",
        "permit_issued": "11/03/2025",
        "valuation": 19000,
        "sqft": 0,
        "contacts": "Gayle Biemeret, Tarrant Roofing - 8179922010 - g-biemeret@sbcglobal.net, Robert Taylor"
    },
    {
        "permit_number": "25-004226",
        "permit_type": "Building - Roofing",
        "description": "RE-ROOF TEAR OFF ONE LAYER GO BACK WITH ONE LAYER 30 YEAR COMP SHINGLE",
        "address": "1216 Berkley Dr.",
        "date_started": "11/03/2025",
        "permit_issued": "11/04/2025",
        "valuation": 13964,
        "sqft": 0,
        "contacts": "Larry Huffaker, Huffaker Roofing - 8173796533 - huffakerroofing@aol.com, Robert Taylor"
    },
    {
        "permit_number": "25-004227",
        "permit_type": "Electrical Permit - MISC",
        "description": "Replacing 200A Panel, adding outside disconnecting means per code",
        "address": "3340 Pecan Hollow Ct.",
        "date_started": "11/03/2025",
        "permit_issued": "11/07/2025",
        "valuation": 4000,
        "sqft": 10,
        "contacts": "Mark Constant, Constant Electric LLC - (469) 233-8985 - markconstant7@gmail.com"
    },
    {
        "permit_number": "25-004228",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Tunnel under slab from backyard and repair leak(s) on sewer line.",
        "address": "1727 Sonnet Dr.",
        "date_started": "11/03/2025",
        "permit_issued": "11/03/2025",
        "valuation": 2500,
        "sqft": 2212,
        "contacts": "Randy DeWeese, RWD Services LLC - 8179998108 - rwdservices1@gmail.com"
    },
    {
        "permit_number": "25-004230",
        "permit_type": "Building - Residential Addition",
        "description": "Converting a patio to a bedroom.",
        "address": "1306 Worthington Dr.",
        "date_started": "11/03/2025",
        "permit_issued": None,
        "valuation": 50000,
        "sqft": 318,
        "contacts": "Jeff Karr, Estate Builders - 4693947373 - jeff@estateadu.com"
    },
    {
        "permit_number": "25-004233",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Reroute 30ft of sewer line in yard",
        "address": "2337 Dove Rd.",
        "date_started": "11/03/2025",
        "permit_issued": "11/03/2025",
        "valuation": 1700,
        "sqft": 1500,
        "contacts": "Larry Stinson, Larry Stinson Plumbing - 8174532008 - support@larrystinsonplumbing.com"
    },
    {
        "permit_number": "25-004234",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Underground sewer replacement.",
        "address": "1338 Mockingbird Dr.",
        "date_started": "11/03/2025",
        "permit_issued": "11/04/2025",
        "valuation": 1000,
        "sqft": 65,
        "contacts": "Mauricio Diaz, Oasis Mechanical LLC - 2146738824 - oasismechanical9@gmail.com"
    },
    {
        "permit_number": "25-004241",
        "permit_type": "Electrical Permit - MISC",
        "description": "Replacing the existing overhead riser and raising it above the roof.",
        "address": "1019 Mockingbird Dr.",
        "date_started": "11/03/2025",
        "permit_issued": "11/03/2025",
        "valuation": 4100,
        "sqft": 2300,
        "contacts": "Jonathan Cardona, J&J Electric, LLC - 8178740636 - jonathan.electric19@gmail.com"
    },
    {
        "permit_number": "25-004243",
        "permit_type": "Building - Residential Addition",
        "description": "Construct a 24x22 Cedar Patio Cover (No Concrete, No Electrical)",
        "address": "9 Whispering Vine Ct.",
        "date_started": "11/03/2025",
        "permit_issued": None,
        "valuation": 13000,
        "sqft": 528,
        "contacts": "Julie Mckissick, TEXAS SELECT RENOVATIONS - 2148461096 - mckissickjulie@yahoo.com"
    },
    {
        "permit_number": "25-004244",
        "permit_type": "Building - Roofing",
        "description": "reroof",
        "address": "1025 Honeysuckle",
        "date_started": "11/04/2025",
        "permit_issued": "11/04/2025",
        "valuation": 14200,
        "sqft": 0,
        "contacts": "Dennis Harrison, HonestRoof.com - 8179662863 - dennis@honestroof.com"
    },
    {
        "permit_number": "25-004245",
        "permit_type": "Electrical Permit",
        "description": "wiring for new production line - Yanwen Express LLC",
        "address": "3193 Bass Pro Dr., 100",
        "date_started": "11/04/2025",
        "permit_issued": "11/05/2025",
        "valuation": 50000,
        "sqft": 35418,
        "contacts": "Gordon Chou, MCG Development LLC - 2145518999 - mcgelectricalcontractor@gmail.com"
    },
    {
        "permit_number": "25-004246",
        "permit_type": "Electrical Permit - MISC",
        "description": "PERMANENT GENERATOR: Generac 26kW standby generator and 200a automatic transfer switch installation.",
        "address": "1721 Parkwood Dr.",
        "date_started": "11/04/2025",
        "permit_issued": "11/05/2025",
        "valuation": 17989,
        "sqft": 2117,
        "contacts": "Andrew Sandefur, GENERATOR SUPERCENTER OF DENTON - 9402183899 - permitsdenton@generatorsupercenter.com"
    },
    {
        "permit_number": "25-004249",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Re-route new water line overhead to bypass line leaking below slab.",
        "address": "1225 Sterling Ln.",
        "date_started": "11/04/2025",
        "permit_issued": "11/04/2025",
        "valuation": 2500,
        "sqft": 1325,
        "contacts": "Randy DeWeese, RWD Services LLC - 8179998108 - rwdservices1@gmail.com"
    },
    {
        "permit_number": "25-004251",
        "permit_type": "Plumbing - Irrigation Permit",
        "description": "Install new residential landscape irrigation",
        "address": "3000 Kosse Ct",
        "date_started": "11/04/2025",
        "permit_issued": "11/10/2025",
        "valuation": 3150,
        "sqft": 7466,
        "contacts": "Jason Lanzara, MDM Lawncare - 8173960125 - warren@mdmlawncare.com"
    },
    {
        "permit_number": "25-004254",
        "permit_type": "Building - Residential Alteration",
        "description": "Repair drywall ceiling and beam repairs",
        "address": "2910 Harvest Hill Dr.",
        "date_started": "11/04/2025",
        "permit_issued": None,
        "valuation": 34159.16,
        "sqft": 2130,
        "contacts": "Sean Kenyon, PROCO Roofing - 4696743670 - skenyon@procoroof.com"
    },
    {
        "permit_number": "25-004255",
        "permit_type": "Mechanical Permit - MISC",
        "description": "Replace Condenser, Evaporator, and Furnace",
        "address": "1949 North Port Ct.",
        "date_started": "11/04/2025",
        "permit_issued": "11/05/2025",
        "valuation": 12801,
        "sqft": 0,
        "contacts": "Scott Peterson, Diamond Quality Services - 8174811786 - scott@diamondqualityservice.com"
    },
    {
        "permit_number": "25-004261",
        "permit_type": "Building - Residential Alteration",
        "description": "Replacing old siding with new Hardie Board siding on the front of the house.",
        "address": "1425 Tiffany Forest Ln.",
        "date_started": "11/04/2025",
        "permit_issued": "11/19/2025",
        "valuation": 2000,
        "sqft": 350,
        "contacts": "Malcolm Hoover, Designer Exteriors - 4695164956 - malcolm@designer-exteriors.com"
    },
    {
        "permit_number": "25-004262",
        "permit_type": "Electrical Permit - MISC",
        "description": "Changing out electrical panel. Adding outlet for EV charger or RV outlet. Adding ATS for future generator.",
        "address": "4320 Country Ln.",
        "date_started": "11/05/2025",
        "permit_issued": "11/05/2025",
        "valuation": 5500,
        "sqft": 1655,
        "contacts": "Dennis Stiles, Dennis Stiles Master Electrician & Company, LLC - 8177732278 - Permits@DS-ME-CO.com"
    },
    {
        "permit_number": "25-004263",
        "permit_type": "Building - Roofing",
        "description": "remove old roof to decking and replace with new synthetic underlayment and new composite asphalt shingles",
        "address": "1916 Everglade Ct.",
        "date_started": "11/05/2025",
        "permit_issued": "11/10/2025",
        "valuation": 10000,
        "sqft": 0,
        "contacts": "Jason Webber, JWC General Contractors, LLC - 2149724266 - permits@jwconstructiongroup.net"
    },
    {
        "permit_number": "25-004264",
        "permit_type": "Building - Church Alteration",
        "description": "construct and sheetrock new walls, install doors on new walls, relocate some electrical",
        "address": "5311 William D Tate Ave.",
        "date_started": "11/05/2025",
        "permit_issued": None,
        "valuation": 46000,
        "sqft": 10000,
        "contacts": "Sarah Ware, Ware Brothers Remodeling LLC - 8177859789 - warebrothersinfo@gmail.com"
    },
    {
        "permit_number": "25-004265",
        "permit_type": "Building - Residential Alteration",
        "description": "French Drains 92 Ft Root Barrier 86 Ft",
        "address": "1929 Fair Field Dr.",
        "date_started": "11/05/2025",
        "permit_issued": None,
        "valuation": 18167,
        "sqft": 178,
        "contacts": "James Oursler, Granite Foundation Repair, Inc. - (972) 412-2171 - claudia@granitefoundationrepair.com"
    },
    {
        "permit_number": "25-004269",
        "permit_type": "Building - Roofing",
        "description": "Reroof",
        "address": "3200 Oak Tree Ln.",
        "date_started": "11/05/2025",
        "permit_issued": "11/06/2025",
        "valuation": 25000,
        "sqft": 0,
        "contacts": "Roger J. Preble, Roger The Roofer LLC - 8175010623 - roger@rogertheroofer.com"
    },
    {
        "permit_number": "25-004271",
        "permit_type": "Building - Roofing",
        "description": "Re-Roof Single Family Residence",
        "address": "4319 Country Ln.",
        "date_started": "11/05/2025",
        "permit_issued": "11/06/2025",
        "valuation": 20000,
        "sqft": 0,
        "contacts": "Thomas Tynes, Upper90 Roofing - 4699512229 - tommy@upper90roofing.com"
    },
    {
        "permit_number": "25-004273",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replace 50 Gallon Gas Water Heater in Garage",
        "address": "1714 Altacrest Dr.",
        "date_started": "11/05/2025",
        "permit_issued": "11/06/2025",
        "valuation": 2100,
        "sqft": 0,
        "contacts": "Jerry Steward, Same Day Water Heater - 9724474949 - permits@samedaywh.com"
    },
    {
        "permit_number": "25-004277",
        "permit_type": "Plumbing - Irrigation Permit",
        "description": "New residential irrigation system",
        "address": "2947 Kosse Ct",
        "date_started": "11/06/2025",
        "permit_issued": "11/11/2025",
        "valuation": 4000,
        "sqft": 6000,
        "contacts": "Jake Reichenstein, Homegrown Irrigation - 8178460903 - jakereichenstein@yahoo.com"
    },
    {
        "permit_number": "25-004284",
        "permit_type": "Plumbing Permit - MISC",
        "description": "replace water service from meter to house",
        "address": "1801 Sonnet Dr.",
        "date_started": "11/06/2025",
        "permit_issued": "11/06/2025",
        "valuation": 3500,
        "sqft": 2000,
        "contacts": "John Klassen, John Klassen, LLC - 9722599600 - johnklasseninc@gmail.com"
    },
    {
        "permit_number": "25-004286",
        "permit_type": "Building - Residential Addition",
        "description": "Construct Attached Patio Cover on New Slab",
        "address": "2606 Evinrude Dr.",
        "date_started": "11/06/2025",
        "permit_issued": None,
        "valuation": 5000,
        "sqft": 2462,
        "contacts": "Ryan Gamill, BME Exteriors - (817) 291-8536 - office@bmeexteriors.com"
    },
    {
        "permit_number": "25-004289",
        "permit_type": "Building - Roofing",
        "description": "Reroofing with same shingle style & quality plus replacing all pipes and vents.",
        "address": "3052 High Cliff Dr.",
        "date_started": "11/06/2025",
        "permit_issued": "11/07/2025",
        "valuation": 39100,
        "sqft": 0,
        "contacts": "Will Merrifield, IFC Roofing - 4698223539 - payroll@ifcroofing.com"
    },
    {
        "permit_number": "25-004290",
        "permit_type": "Plumbing Permit - MISC",
        "description": "90 ft tunnel sewerline repair",
        "address": "205 Ivy Glen Dr.",
        "date_started": "11/07/2025",
        "permit_issued": "11/07/2025",
        "valuation": 20000,
        "sqft": 0,
        "contacts": "Stephen Harris, Berkeys (PLBG) - 8174815869 - rfairchild@berkeys.com"
    },
    {
        "permit_number": "25-004291",
        "permit_type": "Mechanical Permit - MISC",
        "description": "REPLACEMENT OF FURNACE ONLY",
        "address": "3806 Shady Meadow Dr.",
        "date_started": "11/07/2025",
        "permit_issued": "11/07/2025",
        "valuation": 7480,
        "sqft": 3298,
        "contacts": "Sean Stark, Sunny Service - 8177309000 - permits@sunnyservice.com"
    },
    {
        "permit_number": "25-004292",
        "permit_type": "Mechanical Permit - MISC",
        "description": "Replacing 2 Existing HVAC units, complete install with gas furnaces",
        "address": "3317 Moss Creek Dr.",
        "date_started": "11/07/2025",
        "permit_issued": "11/07/2025",
        "valuation": 30000,
        "sqft": 2500,
        "contacts": "Nick Wellborn, Coventry & Gattis A/C, Inc. - 8174814286 - info@coventryandgattis.com"
    },
    {
        "permit_number": "25-004293",
        "permit_type": "Building - Residential Accessory Structures",
        "description": "Storage Shed (12' x 24' x 13' Tall)",
        "address": "1414 Wycliff Ct.",
        "date_started": "11/07/2025",
        "permit_issued": None,
        "valuation": 18000,
        "sqft": 288,
        "contacts": "Steve Felton, BUILDING HOMEOWNER PERMIT"
    },
    {
        "permit_number": "25-004294",
        "permit_type": "Building - Roofing",
        "description": "Roof Recovery - TPO installation",
        "address": "2100 W Northwest Hwy., 202",
        "date_started": "11/07/2025",
        "permit_issued": "11/14/2025",
        "valuation": 220215,
        "sqft": 0,
        "contacts": "Scott Manning, Paragon Roofing, LLC - 2146306363 - accounting@paragonroofingus.com"
    },
    {
        "permit_number": "25-004296",
        "permit_type": "Building - Roofing",
        "description": "re-roof due to storm damage",
        "address": "910 Harber Ave.",
        "date_started": "11/07/2025",
        "permit_issued": "11/07/2025",
        "valuation": 25000,
        "sqft": 0,
        "contacts": "Brad Allen, Arrowhead Roofing - 8176973007 - sales@arrowheadrooftx.com"
    },
    {
        "permit_number": "25-004297",
        "permit_type": "Building - Commercial Alteration",
        "description": "Interior alterations to existing retail space for new retail tenant - Clarks",
        "address": "3000 Grapevine Mills Pkwy., 432",
        "date_started": "11/07/2025",
        "permit_issued": None,
        "valuation": 135000,
        "sqft": 3637,
        "contacts": "Mel Rawls, Mel Rawls Jr - 8035179794 - melrawlsjr@gmail.com"
    },
    {
        "permit_number": "25-004299",
        "permit_type": "Building - Residential Alteration",
        "description": "Replace (1) Window (No Structural Changes)",
        "address": "713 Cable Creek Dr.",
        "date_started": "11/07/2025",
        "permit_issued": "11/18/2025",
        "valuation": 3997,
        "sqft": 0,
        "contacts": "KYLE WILSON, RENEWAL BY ANDERSEN - 9722028400 - zip.permits1@yahoo.com"
    },
    {
        "permit_number": "25-004300",
        "permit_type": "Building - Roofing",
        "description": "Reroofing with same shingle style & quality plus replacing all pipes and vents.",
        "address": "2528 Springhill Dr.",
        "date_started": "11/07/2025",
        "permit_issued": "11/07/2025",
        "valuation": 32361,
        "sqft": 0,
        "contacts": "Will Merrifield, IFC Roofing - 4698223539 - payroll@ifcroofing.com"
    },
    {
        "permit_number": "25-004302",
        "permit_type": "Building - Roofing",
        "description": "Re-Roof Single Family Residence",
        "address": "4336 Kenwood Dr.",
        "date_started": "11/07/2025",
        "permit_issued": "11/07/2025",
        "valuation": 6000,
        "sqft": 0,
        "contacts": "Stephanie Elkins Mandujano, JAM ROOFING - 6825596217 - jamroofing817@gmail.com"
    },
    {
        "permit_number": "25-004303",
        "permit_type": "Fence - Residential",
        "description": "Install 6 Ft Iron Fence",
        "address": "2910 Parr Ln.",
        "date_started": "11/07/2025",
        "permit_issued": "11/26/2025",
        "valuation": 90000,
        "sqft": 0,
        "contacts": "Carly Perez, Lambert's Ornamental Iron - 8175773837 - carly@lambertsiron.com"
    },
    {
        "permit_number": "25-004307",
        "permit_type": "Plumbing Permit - MISC",
        "description": "sewer line spot repair",
        "address": "1227 W Hudgins St.",
        "date_started": "11/07/2025",
        "permit_issued": "11/10/2025",
        "valuation": 9000,
        "sqft": 0,
        "contacts": "Theron Young, Legacy plumbing - 9728019798 - info@legacyplumbing.net"
    },
    {
        "permit_number": "25-004309",
        "permit_type": "Building - Roofing",
        "description": "Remove down to decking; replace underlayment and comp. shingles in single layer",
        "address": "1807 Autumndale Dr.",
        "date_started": "11/07/2025",
        "permit_issued": "11/11/2025",
        "valuation": 15000,
        "sqft": 0,
        "contacts": "Tyler Thomson, PHOENIX CONTRACTING SOLUTIONS - 9452673176 - office@phoenixdfw.com"
    },
    {
        "permit_number": "25-004310",
        "permit_type": "Building - Residential Alteration",
        "description": "PERMANENT GENERATOR: Generac 26kW standby generator",
        "address": "3052 High Cliff Dr.",
        "date_started": "11/08/2025",
        "permit_issued": "11/24/2025",
        "valuation": 18966,
        "sqft": 4114,
        "contacts": "Andrew Sandefur, GENERATOR SUPERCENTER OF DENTON - 9402183899 - permitsdenton@generatorsupercenter.com"
    },
    {
        "permit_number": "25-004313",
        "permit_type": "Plumbing Permit - MISC",
        "description": "water repipe interior overhead",
        "address": "3220 High Meadow Dr.",
        "date_started": "11/09/2025",
        "permit_issued": "11/10/2025",
        "valuation": 5000,
        "sqft": 0,
        "contacts": "Stephen Harris, Berkeys (PLBG) - 8174815869 - rfairchild@berkeys.com"
    },
    {
        "permit_number": "25-004314",
        "permit_type": "Building - Roofing",
        "description": "Scope of work covers, tear off the current roofing system down to clean decking",
        "address": "709 Cory St.",
        "date_started": "11/10/2025",
        "permit_issued": "11/10/2025",
        "valuation": 13261,
        "sqft": 0,
        "contacts": "Sean Kenyon, PROCO Roofing - 4696743670 - skenyon@procoroof.com"
    },
    {
        "permit_number": "25-004315",
        "permit_type": "Building - Roofing",
        "description": "Re Roof",
        "address": "1901 North Port Ct.",
        "date_started": "11/10/2025",
        "permit_issued": "11/10/2025",
        "valuation": 35422,
        "sqft": 0,
        "contacts": "Shaina Weiss, Gotcha Covered Contracting - 8178122703 - shaina@gccroofers.com"
    },
    {
        "permit_number": "25-004316",
        "permit_type": "Building - Residential Alteration",
        "description": "Replace (13) Windows (No Structural Changes)",
        "address": "2825 Greenbrook Ct.",
        "date_started": "11/10/2025",
        "permit_issued": "11/18/2025",
        "valuation": 50670,
        "sqft": 109,
        "contacts": "KYLE WILSON, RENEWAL BY ANDERSEN - 9722028400 - zip.permits1@yahoo.com"
    },
    {
        "permit_number": "25-004321",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replacing the gas water heater in the garage",
        "address": "3257 Oak Tree Ln.",
        "date_started": "11/10/2025",
        "permit_issued": "11/10/2025",
        "valuation": 2300,
        "sqft": 0,
        "contacts": "Joe Dan Parson, ARS Rescue Rooter - 8172221211 - 230-dispatch@ars.com"
    },
    {
        "permit_number": "25-004322",
        "permit_type": "Building - Roofing",
        "description": "Replace Residential Roof",
        "address": "3205 Shady Glen Dr.",
        "date_started": "11/10/2025",
        "permit_issued": "11/17/2025",
        "valuation": 17056,
        "sqft": 0,
        "contacts": "Justin Caldwell, Caldwell Exteriors - 8172916512 - office@caldwellexterior.com"
    },
    {
        "permit_number": "25-004324",
        "permit_type": "Building - Roofing",
        "description": "Roof Shingle Replacement",
        "address": "3201 Shady Glen Dr.",
        "date_started": "11/10/2025",
        "permit_issued": None,
        "valuation": 17727,
        "sqft": 0,
        "contacts": "Justin Caldwell, Caldwell Exteriors - 8172916512 - office@caldwellexterior.com"
    },
    {
        "permit_number": "25-004325",
        "permit_type": "Plumbing Permit - MISC",
        "description": "replace tankless water heater in garage",
        "address": "2734 Hidden Lake Dr.",
        "date_started": "11/10/2025",
        "permit_issued": "11/10/2025",
        "valuation": 2000,
        "sqft": 0,
        "contacts": "TIM DARNELL, TIM DARNELL PLUMBING - 6825571478 - etdarnell@gmail.com"
    },
    {
        "permit_number": "25-004326",
        "permit_type": "Mechanical Permit",
        "description": "replace existing 10 ton York HVAC RTU system with a new York HVAC system - Zales",
        "address": "3000 Grapevine Mills Pkwy., 227",
        "date_started": "11/10/2025",
        "permit_issued": "11/12/2025",
        "valuation": 20000,
        "sqft": 1500,
        "contacts": "Austin Gregg, Infinity AC - 6822334690 - desiree@infinityairco.com"
    },
    {
        "permit_number": "25-004328",
        "permit_type": "Building - Residential Alteration",
        "description": "Install (16) pressed piers for residential foundation repair",
        "address": "1801 Glen Wood Dr.",
        "date_started": "11/10/2025",
        "permit_issued": None,
        "valuation": 10000,
        "sqft": 2000,
        "contacts": "Juan Baca, JB Quality Foundation Repair - 8178966152 - jbqualityfoundation@yahoo.com"
    },
    {
        "permit_number": "25-004329",
        "permit_type": "Building - Roofing",
        "description": "Replace Shingles for Single Family Residence",
        "address": "2717 Brittany Ln.",
        "date_started": "11/10/2025",
        "permit_issued": "11/11/2025",
        "valuation": 25362,
        "sqft": 0,
        "contacts": "Sean Kenyon, PROCO Roofing - 4696743670 - skenyon@procoroof.com"
    },
    {
        "permit_number": "25-004331",
        "permit_type": "Building - Residential Addition",
        "description": "Installing an attached patio cover. 12' x 29' to the residence.",
        "address": "701 Cable Creek Dr.",
        "date_started": "11/10/2025",
        "permit_issued": None,
        "valuation": 35000,
        "sqft": 348,
        "contacts": "Chad Turner, PROvision Outdoor Living - 2148868634 - permits@provisionoutdoorliving.com"
    },
    {
        "permit_number": "25-004332",
        "permit_type": "Plumbing Permit - MISC",
        "description": "REPLACE 20 FT OF WATER REROUTE",
        "address": "4306 Hazy Meadow Ln.",
        "date_started": "11/11/2025",
        "permit_issued": "11/11/2025",
        "valuation": 5600,
        "sqft": 17,
        "contacts": "Joseph Rhoades, A # 1 AIR - 9725120030 - PLUMBINGPERMITS@ANUMBER1AIR.COM"
    },
    {
        "permit_number": "25-004333",
        "permit_type": "Building - Roofing",
        "description": "Scope of work covers, tear off the current roofing system down to clean decking",
        "address": "217 W Peach St.",
        "date_started": "11/11/2025",
        "permit_issued": "11/17/2025",
        "valuation": 6095,
        "sqft": 0,
        "contacts": "Sean Kenyon, PROCO Roofing - 4696743670 - skenyon@procoroof.com"
    },
    {
        "permit_number": "25-004344",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Water repair by tunnel - up to 8'",
        "address": "3860 Lakeway Dr.",
        "date_started": "11/11/2025",
        "permit_issued": "11/11/2025",
        "valuation": 8300,
        "sqft": 0,
        "contacts": "Jeff Sims, billyGO DFW, LLC - 8177226151 - dottie@billygo.com"
    },
    {
        "permit_number": "25-004345",
        "permit_type": "Building - Residential Addition",
        "description": "Addition of (549 SF) to Existing 1863 SF Residence",
        "address": "4125 Windomere Dr.",
        "date_started": "11/11/2025",
        "permit_issued": None,
        "valuation": 85000,
        "sqft": 1327,
        "contacts": "Rob Coppola, All N Renovations & Roofing - 4697814833 - allnrenovations@gmail.com"
    },
    {
        "permit_number": "25-004346",
        "permit_type": "Building - Residential Addition",
        "description": "Remodel with addition and partial demo of the current house.",
        "address": "508 E Worth St.",
        "date_started": "11/11/2025",
        "permit_issued": None,
        "valuation": 800000,
        "sqft": 2500,
        "contacts": "Nick Heitz, Homestead Custom Homes - 8179259914 - nheitz@tpabaseball.com"
    },
    {
        "permit_number": "25-004347",
        "permit_type": "Building - Commercial Alteration",
        "description": "Interior Alteration of Existing Office Building for New Tenant - Bible Study Fellowship",
        "address": "2700 Western Oaks Dr.",
        "date_started": "11/12/2025",
        "permit_issued": None,
        "valuation": 14586394,
        "sqft": 53103,
        "contacts": "Curtis Walker, MAPP, LLC - 2142195075 - cwalker@mappbuilt.com"
    },
    {
        "permit_number": "25-004350",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Plumber will locate and cap off line leaking below slab. Plumber will reroute waterline above slab.",
        "address": "500 Coventry Dr.",
        "date_started": "11/12/2025",
        "permit_issued": "11/12/2025",
        "valuation": 2450,
        "sqft": 2417,
        "contacts": "Mark Ondras Plumbing LLC - 8178458986 - markondrasplumbingllc@gmail.com"
    },
    {
        "permit_number": "25-004351",
        "permit_type": "Electrical Permit - MISC",
        "description": "Installation of a 10.44kW roof mount PV solar system.",
        "address": "330 N Dove Rd.",
        "date_started": "11/12/2025",
        "permit_issued": None,
        "valuation": 27479,
        "sqft": 505,
        "contacts": "Adrian Buck, Freedom Solar Power - 5128152949 - permitting@freedomsolarpower.com"
    },
    {
        "permit_number": "25-004359",
        "permit_type": "Building - Roofing",
        "description": "Remove existing asphalt shingles and install new asphalt shingles. Installing Certainteed Landmark",
        "address": "2720 Indian Oak Dr.",
        "date_started": "11/12/2025",
        "permit_issued": "11/13/2025",
        "valuation": 30162,
        "sqft": 0,
        "contacts": "Corey Peters, Texas Premier Roofing LLC - 4692477752 - info@txpremierroofing.com"
    },
    {
        "permit_number": "25-004363",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replacing PRV & whole home water shut off valve",
        "address": "807 Redbud Ln.",
        "date_started": "11/12/2025",
        "permit_issued": "11/13/2025",
        "valuation": 3500,
        "sqft": 0,
        "contacts": "Shanna Nevil, Milestone Plumbing - 9725265926 - Shanna@Callmilestone.com"
    },
    {
        "permit_number": "25-004374",
        "permit_type": "Building - Roofing",
        "description": "Residential Reroof",
        "address": "1909 Tanglewood Dr.",
        "date_started": "11/12/2025",
        "permit_issued": "11/13/2025",
        "valuation": 20725,
        "sqft": 0,
        "contacts": "DUSTIN REILING, ROOFTOP SOLUTIONS DFW - 7637446944 - KRYSTAL@ROOFTOPSOLUTIONSDFW.COM"
    },
    {
        "permit_number": "25-004375",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Run gas line for gas cooktop - up to 35'",
        "address": "2918 Robindale Ln.",
        "date_started": "11/12/2025",
        "permit_issued": "11/13/2025",
        "valuation": 3860,
        "sqft": 0,
        "contacts": "Jeff Sims, billyGO DFW, LLC - 8177226151 - dottie@billygo.com"
    },
    {
        "permit_number": "25-004377",
        "permit_type": "Plumbing Permit - MISC",
        "description": "water leak repair below concrete drive way",
        "address": "1459 Hampton Rd.",
        "date_started": "11/13/2025",
        "permit_issued": "11/14/2025",
        "valuation": 4000,
        "sqft": 1645,
        "contacts": "Clayton Robinson, CR Plumbing - 9403673778 - crplumbingdfw@gmail.com"
    },
    {
        "permit_number": "25-004378",
        "permit_type": "Building - Residential Alteration",
        "description": "Installation of a 10.44kW roof mounted PV solar system",
        "address": "330 N Dove Rd.",
        "date_started": "11/13/2025",
        "permit_issued": None,
        "valuation": 27479,
        "sqft": 505,
        "contacts": "Adrian Buck, Freedom Solar Power - 5128152949 - permitting@freedomsolarpower.com"
    },
    {
        "permit_number": "25-004380",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Clean out replacement in front yard - 4 feet",
        "address": "2843 Panhandle Dr.",
        "date_started": "11/13/2025",
        "permit_issued": "11/13/2025",
        "valuation": 5500,
        "sqft": 1563,
        "contacts": "Johnathan White, TopTech Electric & Plumbing - 6822625759 - info@calltoptech.com"
    },
    {
        "permit_number": "25-004382",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replacing 95 ft of sewer main",
        "address": "2823 Newcastle Dr.",
        "date_started": "11/13/2025",
        "permit_issued": "11/14/2025",
        "valuation": 5800,
        "sqft": 2900,
        "contacts": "ARMANDO RIVERA, IMA PLUMBING LLC - 8179447925 - armando@imaplumbing.com"
    },
    {
        "permit_number": "25-004383",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replace 50 Gal Gas Water Heater.",
        "address": "2807 Kimberly Dr.",
        "date_started": "11/13/2025",
        "permit_issued": "11/13/2025",
        "valuation": 3181,
        "sqft": 0,
        "contacts": "Ira Preuett, Max Heating & Cooling LLC dba Willard - 8174594100 - bryinna.waddle@maxair.com"
    },
    {
        "permit_number": "25-004384",
        "permit_type": "Mechanical Permit GU & ISD ALT/MISC",
        "description": "Replace chiller for new - Hotel Vin",
        "address": "815 S Main St.",
        "date_started": "11/13/2025",
        "permit_issued": "11/14/2025",
        "valuation": 346987,
        "sqft": 152,
        "contacts": "Steve Humphrey, Sr., Humphrey & Associates, Inc. - 9726201075 - lorim@teamhumphrey.com"
    },
    {
        "permit_number": "25-004386",
        "permit_type": "Plumbing Permit - MISC",
        "description": "2 Access hole in dirt, up to 20 feet of tunnel to repair existing sewer.",
        "address": "3044 Old Mill Run",
        "date_started": "11/13/2025",
        "permit_issued": "11/13/2025",
        "valuation": 2100,
        "sqft": 400,
        "contacts": "Eric Lawson, Black Tie Plumbing - 8173728818 - info@blacktieplumbing.com"
    },
    {
        "permit_number": "25-004389",
        "permit_type": "Building - Residential Alteration",
        "description": "Replace (2) Windows and (1) Door and replace with (3) panel sliders",
        "address": "2900 Trail Lake Dr.",
        "date_started": "11/13/2025",
        "permit_issued": None,
        "valuation": 6570,
        "sqft": 85,
        "contacts": "Jennifer Parker, Love That Door - 9726706690 - lovethatdoor24@gmail.com"
    },
    {
        "permit_number": "25-004401",
        "permit_type": "Building - Residential Alteration",
        "description": "Replace (22) Windows (No Structural Changes)",
        "address": "1824 Haydenbend Cir.",
        "date_started": "11/14/2025",
        "permit_issued": "11/24/2025",
        "valuation": 17085,
        "sqft": 197,
        "contacts": "DAX KIRKS, BEST BUY WINDOWS AND SIDING - 9726706690 - bestbuywindowsandsiding@yahoo.com"
    },
    {
        "permit_number": "25-004405",
        "permit_type": "Building - Roofing",
        "description": "Reroofing with same shingle style & quality plus replacing all pipes and vents.",
        "address": "539 Post Oak Rd.",
        "date_started": "11/14/2025",
        "permit_issued": "11/17/2025",
        "valuation": 26420,
        "sqft": 0,
        "contacts": "Will Merrifield, IFC Roofing - 4698223539 - payroll@ifcroofing.com"
    },
    {
        "permit_number": "25-004409",
        "permit_type": "Building - Single Family Residence",
        "description": "New Single Family Residential",
        "address": "1225 Murrell Rd.",
        "date_started": "11/17/2025",
        "permit_issued": None,
        "valuation": 1150000,
        "sqft": 5231,
        "contacts": "Carey Caldwell, CCH Builders - 9728801710 - carey.caldwell@sbcglobal.net"
    },
    {
        "permit_number": "25-004410",
        "permit_type": "Plumbing Permit",
        "description": "replace the deteriorated sewer line located in the corridor near Restroom Group #4, Tunneling approximately 100 feet in total",
        "address": "3000 Grapevine Mills Pkwy., Shell",
        "date_started": "11/17/2025",
        "permit_issued": "11/17/2025",
        "valuation": 66923,
        "sqft": 1325709,
        "contacts": "Lawton Services - 9724242929 - service@lawtonpros.com"
    },
    {
        "permit_number": "25-004412",
        "permit_type": "Mechanical Permit - MISC",
        "description": "REPLACE 5 TON GAS AC",
        "address": "2907 Valleyview Dr.",
        "date_started": "11/17/2025",
        "permit_issued": "11/21/2025",
        "valuation": 18873,
        "sqft": 0,
        "contacts": "JAMES GREEN, A #1 AIR - 9725120030 - PERMITS@ANUMBER1AIR.COM"
    },
    {
        "permit_number": "25-004417",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Tunnel 10' to address a sewer break under the slab",
        "address": "3317 Clearfield Dr.",
        "date_started": "11/17/2025",
        "permit_issued": "11/19/2025",
        "valuation": 9700,
        "sqft": 0,
        "contacts": "Chris Edmonds, CWE Group INC - 9723952597 - permits@CandWplumbing.com"
    },
    {
        "permit_number": "25-004429",
        "permit_type": "Building - Residential Addition",
        "description": "Alterations to exterior and interior with moving the exterior wall out to open up the interior living space.",
        "address": "3224 Fannin Ln.",
        "date_started": "11/17/2025",
        "permit_issued": None,
        "valuation": 60000,
        "sqft": 180,
        "contacts": "Neel Dotson, Windsor Pro Contracting - 9727407104 - neeldot@gmail.com"
    },
    {
        "permit_number": "25-004430",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Repair sewer line",
        "address": "1834 Camelot Dr.",
        "date_started": "11/17/2025",
        "permit_issued": "11/17/2025",
        "valuation": 17800,
        "sqft": 1500,
        "contacts": "Larry Stinson, Larry Stinson Plumbing - 8174532008 - support@larrystinsonplumbing.com"
    },
    {
        "permit_number": "25-004436",
        "permit_type": "Building - Roofing",
        "description": "Scope of work covers, tear off the current roofing system down to clean decking",
        "address": "1804 Camelot Dr.",
        "date_started": "11/17/2025",
        "permit_issued": "11/24/2025",
        "valuation": 30570,
        "sqft": 0,
        "contacts": "Sean Kenyon, PROCO Roofing - 4696743670 - skenyon@procoroof.com"
    },
    {
        "permit_number": "25-004437",
        "permit_type": "Building - Roofing",
        "description": "Replace Residential roof",
        "address": "2824 Southshore Dr.",
        "date_started": "11/17/2025",
        "permit_issued": "11/18/2025",
        "valuation": 17002,
        "sqft": 0,
        "contacts": "Jason Armstrong, Quick Roofing, LLC - 8174770999 - permits@quickroofing.com"
    },
    {
        "permit_number": "25-004453",
        "permit_type": "Building - Residential Accessory Structures",
        "description": "Detached Patio Cover/Kitchen on Existing Slab",
        "address": "516 Lucas Dr.",
        "date_started": "11/18/2025",
        "permit_issued": None,
        "valuation": 100000,
        "sqft": 780,
        "contacts": "Nick Teer, Neighborhood Patios LLC - 6822188361 - nick@neighborhoodpatios.com"
    },
    {
        "permit_number": "25-004461",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replace 50 gallon gas water heater",
        "address": "1569 Tiffany Forest Ln.",
        "date_started": "11/18/2025",
        "permit_issued": "11/18/2025",
        "valuation": 3100,
        "sqft": 0,
        "contacts": "BAKER BROTHERS PLUMBING, AIR & ELECTRIC - 2143248811 - angelicamorgan@bakerbrothersplumbing.com"
    },
    {
        "permit_number": "25-004464",
        "permit_type": "Building - Residential Addition",
        "description": "Construct Deck attached to back of the house, Pour Slab For Shed",
        "address": "4358 Eastwoods Dr.",
        "date_started": "11/18/2025",
        "permit_issued": None,
        "valuation": 27829.74,
        "sqft": 480,
        "contacts": "Shawn Brock, Superior One Roofing and Construction - 2148926101 - shawn@superioroneroofing.com"
    },
    {
        "permit_number": "25-004465",
        "permit_type": "Building - Residential Alteration",
        "description": "Install (6) exterior piers for residential foundation",
        "address": "4307 Windswept Ln.",
        "date_started": "11/18/2025",
        "permit_issued": None,
        "valuation": 6893,
        "sqft": 324,
        "contacts": "Richard Childers, Abacus Industries LLC, dba Abacus Foundation Repair - 9724069000 - abacusfoundation@sbcglobal.net"
    },
    {
        "permit_number": "25-004473",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replace 50 gal gas water heater in the garage",
        "address": "2713 Chatsworth Dr.",
        "date_started": "11/19/2025",
        "permit_issued": "11/19/2025",
        "valuation": 3100,
        "sqft": 0,
        "contacts": "Ron Tierney, Tierney Plumbing - 8172519292 - admin@tierneyplumbing.com"
    },
    {
        "permit_number": "25-004474",
        "permit_type": "Plumbing Permit - MISC",
        "description": "replace 1- 50 gallon water heater",
        "address": "602 Huntington Ct.",
        "date_started": "11/19/2025",
        "permit_issued": "11/19/2025",
        "valuation": 2500,
        "sqft": 2000,
        "contacts": "Stephen Harris, Berkeys (PLBG) - 8174815869 - rfairchild@berkeys.com"
    },
    {
        "permit_number": "25-004476",
        "permit_type": "Building - Swimming Pool",
        "description": "Installation of inground pool and decking (CA #25-70)",
        "address": "736 E Wall St.",
        "date_started": "11/19/2025",
        "permit_issued": None,
        "valuation": 58000,
        "sqft": 0,
        "contacts": "Tom Dahnke, Puryear Pools - 8173065169 - tom@puryearpools.com"
    },
    {
        "permit_number": "25-004477",
        "permit_type": "Building - Residential Alteration",
        "description": "Install (17) concrete piers for foundation repair",
        "address": "710 Cory St.",
        "date_started": "11/19/2025",
        "permit_issued": None,
        "valuation": 10521,
        "sqft": 984,
        "contacts": "William Thomas, Accurate Foundation Repair, LLC - 8175619339 - denisec@steelpiers.com"
    },
    {
        "permit_number": "25-004483",
        "permit_type": "Building - Roofing",
        "description": "Remove existing roof and replace with Owens Corning Storm Class 4 (Driftwood)",
        "address": "3076 High Ridge Dr.",
        "date_started": "11/20/2025",
        "permit_issued": "11/20/2025",
        "valuation": 36773,
        "sqft": 0,
        "contacts": "Jason Armstrong, Quick Roofing, LLC - 8174770999 - permits@quickroofing.com"
    },
    {
        "permit_number": "25-004484",
        "permit_type": "Building - Commercial Alteration",
        "description": "Install Access Control - Baylor Scott & White Medical Center",
        "address": "1650 W College # 1 St.",
        "date_started": "11/20/2025",
        "permit_issued": None,
        "valuation": 29978,
        "sqft": 0,
        "contacts": "Bobby Ferguson, Cobalt FTS - 9727927793 - bferguson@fts-dfw.com"
    },
    {
        "permit_number": "25-004488",
        "permit_type": "Plumbing - Irrigation Permit",
        "description": "Install new residential irrigation system",
        "address": "914 Hummingbird Trl.",
        "date_started": "11/20/2025",
        "permit_issued": None,
        "valuation": 4000,
        "sqft": 13400,
        "contacts": "Jake Reichenstein, Homegrown Irrigation - 8178460903 - jakereichenstein@yahoo.com"
    },
    {
        "permit_number": "25-004489",
        "permit_type": "Electrical Permit - MISC",
        "description": "Replacing panel and installing emergency disconnect",
        "address": "3015 Creekview Dr.",
        "date_started": "11/20/2025",
        "permit_issued": "11/20/2025",
        "valuation": 8200,
        "sqft": 0,
        "contacts": "David Acebedo, Good Guys Electric LLC - 6824506407 - goodguyselectric23@gmail.com"
    },
    {
        "permit_number": "25-004493",
        "permit_type": "Building - Residential Addition",
        "description": "Replacing patio attached cover and concrete pad. 220 sq.ft.",
        "address": "3305 Sprindeltree Dr.",
        "date_started": "11/20/2025",
        "permit_issued": None,
        "valuation": 13700,
        "sqft": 220,
        "contacts": "Karina Garcia, Garcias Concrete - (817) 879-4645 - concrete.garcia@gmail.com"
    },
    {
        "permit_number": "25-004494",
        "permit_type": "Building - Roofing",
        "description": "reroof",
        "address": "2145 Lake Crest Dr.",
        "date_started": "11/20/2025",
        "permit_issued": "11/21/2025",
        "valuation": 16000,
        "sqft": 0,
        "contacts": "Gayle Biemeret, Tarrant Roofing - 8179922010 - g-biemeret@sbcglobal.net"
    },
    {
        "permit_number": "25-004495",
        "permit_type": "Building - Swimming Pool",
        "description": "Install Gunite Swimming Pool & Masonry Fire Pit",
        "address": "1921 Lilac Ln.",
        "date_started": "11/21/2025",
        "permit_issued": None,
        "valuation": 95000,
        "sqft": 0,
        "contacts": "WATERCREST POOLS - 8174318997 - LAUREN@WATERCRESTPOOLS.COM"
    },
    {
        "permit_number": "25-004496",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Sewer line spot repair under the home.",
        "address": "3132 Stone Creek Ln.",
        "date_started": "11/21/2025",
        "permit_issued": "11/21/2025",
        "valuation": 929,
        "sqft": 55,
        "contacts": "William Lopez, Du-West Services - 4692006577 - William@Du-West.com"
    },
    {
        "permit_number": "25-004501",
        "permit_type": "Plumbing Permit - MISC",
        "description": "50 gal water heater replacement",
        "address": "2708 Chase Oak Dr.",
        "date_started": "11/23/2025",
        "permit_issued": "11/25/2025",
        "valuation": 1900,
        "sqft": 0,
        "contacts": "Stephen Harris, Berkeys (PLBG) - 8174815869 - rfairchild@berkeys.com"
    },
    {
        "permit_number": "25-004502",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Trench from meter to cutoff at front of house and replace water line.",
        "address": "1477 Hampton Rd.",
        "date_started": "11/24/2025",
        "permit_issued": "11/24/2025",
        "valuation": 2500,
        "sqft": 1599,
        "contacts": "Randy DeWeese, RWD Services LLC - 8179998108 - rwdservices1@gmail.com"
    },
    {
        "permit_number": "25-004503",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Trench from meter to cutoff at front of house and replace water line.",
        "address": "1029 S Riverside Dr.",
        "date_started": "11/24/2025",
        "permit_issued": "11/24/2025",
        "valuation": 2500,
        "sqft": 1325,
        "contacts": "Randy DeWeese, RWD Services LLC - 8179998108 - rwdservices1@gmail.com"
    },
    {
        "permit_number": "25-004504",
        "permit_type": "Building - Residential Alteration",
        "description": "Install (8) concrete piers for foundation repair",
        "address": "420 E College St.",
        "date_started": "11/24/2025",
        "permit_issued": None,
        "valuation": 12798.87,
        "sqft": 69,
        "contacts": "Hayden Slack, GL Hunt Foundation Repair - 8179521435 - production@glhunt.com"
    },
    {
        "permit_number": "25-004505",
        "permit_type": "Building - Residential Alteration",
        "description": "Install (7) concrete piers for foundation repair",
        "address": "2917 Brookshire Dr.",
        "date_started": "11/24/2025",
        "permit_issued": None,
        "valuation": 8693,
        "sqft": 63,
        "contacts": "Hayden Slack, GL Hunt Foundation Repair - 8179521435 - production@glhunt.com"
    },
    {
        "permit_number": "25-004510",
        "permit_type": "Mechanical Permit - MISC",
        "description": "Replace HVAC equipment",
        "address": "3431 Marsh Ln.",
        "date_started": "11/24/2025",
        "permit_issued": "12/01/2025",
        "valuation": 17397,
        "sqft": 2961,
        "contacts": "GRAYE ROBERTS, Moss Mechanical - 9724659966 - permits@mossmechanical.com"
    },
    {
        "permit_number": "25-004519",
        "permit_type": "Building - Residential Alteration",
        "description": "Install Residential Generator",
        "address": "3710 Kelsey Ct.",
        "date_started": "11/25/2025",
        "permit_issued": None,
        "valuation": 15439,
        "sqft": 0,
        "contacts": "Karen Staton, CIRCLE A ELECTRIC - 8176250880 - karen@circleaelectric.com"
    },
    {
        "permit_number": "25-004520",
        "permit_type": "Mechanical Permit - MISC",
        "description": "HVAC Change Out – Remove & Replace 1 full HVAC system located in the attic",
        "address": "3529 Quail Crest Dr.",
        "date_started": "11/25/2025",
        "permit_issued": "11/25/2025",
        "valuation": 11358,
        "sqft": 2495,
        "contacts": "JEFFREY STEWART, Reliant Air Conditioning - 8176161100 - Lrichey@reliantac.com"
    },
    {
        "permit_number": "25-004521",
        "permit_type": "Plumbing Permit - MISC",
        "description": "sewer line spot repair that turned into a sewer line replacement that turned into a whole house repipe",
        "address": "1225 W Hudgins St.",
        "date_started": "11/25/2025",
        "permit_issued": "11/25/2025",
        "valuation": 16850,
        "sqft": 1482,
        "contacts": "Theron Young, Legacy plumbing - 9728019798 - info@legacyplumbing.net"
    },
    {
        "permit_number": "25-004522",
        "permit_type": "Building - Roofing",
        "description": "Remove storm damaged asphalt shingle roof and replace with new asphalt shingle roofing system.",
        "address": "2154 Willowood Dr.",
        "date_started": "11/25/2025",
        "permit_issued": "11/25/2025",
        "valuation": 24448.53,
        "sqft": 0,
        "contacts": "Pius Coles, We Roof Dallas, Inc - 9726008259 - pius@weroofdallas.com"
    },
    {
        "permit_number": "25-004524",
        "permit_type": "Electrical Permit - MISC",
        "description": "Upgrade 200 amp panel, Upgrade 200 amp meter base, Update ground rod and wire",
        "address": "938 S Riverside Dr.",
        "date_started": "11/25/2025",
        "permit_issued": "11/25/2025",
        "valuation": 8200,
        "sqft": 2027,
        "contacts": "Johnathan White, TopTech Electric & Plumbing - 6822625759 - info@calltoptech.com"
    },
    {
        "permit_number": "25-004525",
        "permit_type": "Building - Commercial Alteration",
        "description": "Alterations to the CT Scan Room - BAYLOR SCOTT & WHITE MEDICAL CENTER",
        "address": "1650 W College # 1 St.",
        "date_started": "11/25/2025",
        "permit_issued": None,
        "valuation": 502000,
        "sqft": 650,
        "contacts": "Adam Brown, The Skiles Group - abrown@skilesgroup.com"
    },
    {
        "permit_number": "25-004526",
        "permit_type": "Building - Residential Alteration",
        "description": "Interior Alteration of Resident.",
        "address": "503 Bluebonnet Dr.",
        "date_started": "11/25/2025",
        "permit_issued": None,
        "valuation": 60000,
        "sqft": 119,
        "contacts": "Grant GOMEZ, Cowboy Hardware - 6027573497 - grant@cowboyhardware.com"
    },
    {
        "permit_number": "25-004527",
        "permit_type": "Building - Commercial Alteration",
        "description": "Alteration to existing Cath Lab (Enabling project)",
        "address": "1650 W College # 1 St.",
        "date_started": "11/25/2025",
        "permit_issued": None,
        "valuation": 242000,
        "sqft": 985,
        "contacts": "Adam Brown, The Skiles Group - abrown@skilesgroup.com"
    },
    {
        "permit_number": "25-004531",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replace hot water heater",
        "address": "1332 Martin Ct.",
        "date_started": "11/25/2025",
        "permit_issued": "11/25/2025",
        "valuation": 2987,
        "sqft": 1830,
        "contacts": "Rick Thornton, AIRCO LTD - 8175900088 - JBROOKSHIRE@AIRCO.COM"
    },
    {
        "permit_number": "25-004535",
        "permit_type": "Mechanical Permit - MISC",
        "description": "New 4-Ton HVAC system",
        "address": "2013 Wedgewood Dr.",
        "date_started": "11/25/2025",
        "permit_issued": "11/26/2025",
        "valuation": 13700,
        "sqft": 1600,
        "contacts": "Lindsey Conn, Toms Mechanical Inc - 8172774493 - lindsey.conn@tomsmechanical.com"
    },
    {
        "permit_number": "25-004538",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replacing 50 gallon gas water heater",
        "address": "1521 Bennington Ct.",
        "date_started": "11/26/2025",
        "permit_issued": None,
        "valuation": 3052,
        "sqft": 0,
        "contacts": "Shanna Nevil, Milestone Plumbing - 9725265926 - Shanna@Callmilestone.com"
    },
    {
        "permit_number": "25-004539",
        "permit_type": "Building - Residential Alteration",
        "description": "REPLACE 16 WINDOWS LIKE FOR LIKE",
        "address": "5118 Heatherdale Dr.",
        "date_started": "11/26/2025",
        "permit_issued": None,
        "valuation": 55000,
        "sqft": 0,
        "contacts": "Christopher Derr, Marvin Replacement - chris.derr@marvin.com"
    },
    {
        "permit_number": "25-004543",
        "permit_type": "Plumbing Permit - MISC",
        "description": "install (1) 50 gal gas water heater in garage closet (change out)",
        "address": "3520 Boxwood Dr.",
        "date_started": "11/26/2025",
        "permit_issued": "12/01/2025",
        "valuation": 2000,
        "sqft": 0,
        "contacts": "Jerry Steward, Same Day Water Heater - 9724474949 - permits@samedaywh.com"
    },
    {
        "permit_number": "25-004545",
        "permit_type": "Plumbing Permit - MISC",
        "description": "Replace main water line in front yard.",
        "address": "3224 Shady Glen Dr.",
        "date_started": "11/26/2025",
        "permit_issued": "12/01/2025",
        "valuation": 2500,
        "sqft": 2238,
        "contacts": "Nick Irland, On Point Plumbing - 4692756994 - onpointplumbingdfw@gmail.com"
    },
    {
        "permit_number": "25-004547",
        "permit_type": "Fence - Residential",
        "description": "Installing Fence in same location as existing fence. 6' tall with western red cedar lumber and metal posts.",
        "address": "3052 Ridgeview Dr.",
        "date_started": "11/30/2025",
        "permit_issued": None,
        "valuation": 11000,
        "sqft": 0,
        "contacts": "Scott Williamson, Tin Star Fencing - (817) 992-1300 - swilliamson@tsfencing.com"
    },
    {
        "permit_number": "25-004548",
        "permit_type": "Building - Residential Alteration",
        "description": "1 window replacement, like for like",
        "address": "2800 Woodhaven Dr.",
        "date_started": "11/30/2025",
        "permit_issued": None,
        "valuation": 1200,
        "sqft": 17,
        "contacts": "Carrie Owsley, Install Partners - 8173681832 - carrie@installpartners.net"
    },
    {
        "permit_number": "25-004549",
        "permit_type": "Building - Roofing",
        "description": "Reroofing with same shingle style & quality plus replacing all pipes and vents.",
        "address": "1852 Glen Wood Dr.",
        "date_started": "11/30/2025",
        "permit_issued": None,
        "valuation": 26529,
        "sqft": 0,
        "contacts": "Will Merrifield, IFC Roofing - 4698223539 - payroll@ifcroofing.com"
    },
]


def parse_contact_info(contact_str):
    """Extract contractor name, phone, and email from contact string."""
    result = {
        "contractor_name": None,
        "phone": None,
        "email": None
    }

    if not contact_str:
        return result

    # Extract email (pattern: xxx@xxx.xxx)
    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', contact_str)
    if email_match:
        result["email"] = email_match.group()

    # Extract phone (pattern: 10 digits, with or without formatting)
    phone_match = re.search(r'[\d\-\(\)\s]{10,}', contact_str)
    if phone_match:
        phone = re.sub(r'[^\d]', '', phone_match.group())
        if len(phone) >= 10:
            result["phone"] = phone[:10]

    # Extract contractor name (usually first part before comma or phone)
    parts = contact_str.split(',')
    if parts:
        # Look for company name (usually contains LLC, Inc, etc.)
        for part in parts:
            part = part.strip()
            if any(x in part for x in ['LLC', 'Inc', 'Company', 'Corp', 'Services', 'Roofing', 'Plumbing', 'Electric', 'HVAC', 'Construction', 'Pools']):
                result["contractor_name"] = part.split(' - ')[0].strip()
                break

        # If no company found, use first name/business
        if not result["contractor_name"] and parts[0]:
            name_part = parts[0].strip()
            if not any(x in name_part for x in ['HOMEOWNER', 'DOCUMENTATION']):
                result["contractor_name"] = name_part

    return result


def categorize_permit(permit_type, description):
    """Categorize permit into standard categories."""
    permit_type_lower = permit_type.lower() if permit_type else ""
    desc_lower = description.lower() if description else ""

    # Pool
    if "pool" in permit_type_lower or "pool" in desc_lower:
        return "Pool/Spa"

    # Roofing
    if "roof" in permit_type_lower or "reroof" in desc_lower or "shingle" in desc_lower:
        return "Roofing"

    # Plumbing
    if "plumb" in permit_type_lower or "sewer" in desc_lower or "water heater" in desc_lower or "water line" in desc_lower:
        return "Plumbing"

    # Electrical
    if "electric" in permit_type_lower or "generator" in desc_lower or "solar" in desc_lower or "panel" in desc_lower:
        return "Electrical"

    # HVAC
    if "mechanical" in permit_type_lower or "hvac" in desc_lower or "furnace" in desc_lower or "condenser" in desc_lower:
        return "HVAC"

    # Foundation
    if "foundation" in desc_lower or "piers" in desc_lower:
        return "Foundation"

    # Fence
    if "fence" in permit_type_lower or "fence" in desc_lower:
        return "Fence/Deck"

    # Patio/Outdoor
    if "patio" in desc_lower or "pergola" in desc_lower or "deck" in desc_lower:
        return "Outdoor Living"

    # Windows/Doors
    if "window" in desc_lower or "door" in desc_lower or "siding" in desc_lower:
        return "Windows/Doors"

    # Addition/Remodel
    if "addition" in permit_type_lower or "alteration" in permit_type_lower or "remodel" in desc_lower:
        return "Addition/Remodel"

    # New Construction
    if "single family" in permit_type_lower or "new construction" in desc_lower:
        return "New Construction"

    # Commercial
    if "commercial" in permit_type_lower:
        return "Commercial"

    # Irrigation
    if "irrigation" in permit_type_lower or "irrigation" in desc_lower:
        return "Irrigation"

    return "Other"


def convert_to_standard_format():
    """Convert Grapevine permits to standard JSON format for loading."""
    permits = []

    for p in GRAPEVINE_PERMITS:
        contact_info = parse_contact_info(p.get("contacts", ""))
        category = categorize_permit(p.get("permit_type", ""), p.get("description", ""))

        permit = {
            "permit_id": p["permit_number"],  # load_permits.py expects permit_id
            "permit_type": p.get("permit_type", ""),
            "description": p.get("description", ""),
            "address": p.get("address", ""),
            "city": "Grapevine",
            "issued_date": p.get("permit_issued") or p.get("date_started"),  # load_permits.py expects issued_date
            "value": p.get("valuation", 0),  # load_permits.py expects value
            "sqft": p.get("sqft", 0),
            "contractor_name": contact_info["contractor_name"],
            "contractor_phone": contact_info["phone"],
            "contractor_email": contact_info["email"],
            "category": category,
            "source": "mygov_pdf",
            "raw_contacts": p.get("contacts", "")
        }
        permits.append(permit)

    return permits


def main():
    """Main function to parse and save Grapevine permits."""
    output_dir = Path(__file__).parent.parent / "data" / "raw"
    output_dir.mkdir(parents=True, exist_ok=True)

    permits = convert_to_standard_format()

    output_file = output_dir / "grapevine_mygov_nov2025.json"
    with open(output_file, 'w') as f:
        json.dump(permits, f, indent=2)

    print(f"Saved {len(permits)} permits to {output_file}")

    # Print summary by category
    print("\n=== Permit Summary by Category ===")
    categories = {}
    for p in permits:
        cat = p["category"]
        if cat not in categories:
            categories[cat] = {"count": 0, "valuation": 0}
        categories[cat]["count"] += 1
        categories[cat]["valuation"] += p.get("valuation", 0) or 0

    for cat, data in sorted(categories.items(), key=lambda x: x[1]["count"], reverse=True):
        print(f"  {cat}: {data['count']} permits (${data['valuation']:,.0f} total)")

    # Print contractors with contact info
    print("\n=== Contractors with Contact Info ===")
    contractors_with_info = [p for p in permits if p.get("contractor_name") and (p.get("contractor_phone") or p.get("contractor_email"))]
    print(f"  {len(contractors_with_info)} of {len(permits)} permits have contractor contact info")


if __name__ == "__main__":
    main()
