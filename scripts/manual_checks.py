"""Manual acceptance catalogue and isolated, one-case-at-a-time checks.

This utility never changes application settings, secrets, or running servers.
Controlled checks block real HTTP requests. UI cases remain manual.
"""
import argparse
import copy
import csv
import json
import math
import os
from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
CASES = []


def add(identifier, area, category, sample, steps, expected, spec=None, priority='P1', mode=None):
    CASES.append({'ID': identifier, 'Area': area, 'Category': category,
                  'Priority': priority, 'Method': mode or ('Controlled' if spec else 'Browser'),
                  'Sample inputs': sample, 'Steps': steps, 'Expected result': expected,
                  'Status': 'Not run', 'Actual result': '', 'Notes or evidence': '', '_spec': spec})


def risk_case(identifier, area, sample, wind=0, rain=0, snow=0, load=10000, level='Low', complete=True, category='Boundary'):
    weather = {'wind_mph': wind, 'rain_in_per_hour': rain, 'snow_in_per_hour': snow}
    expected = {'level': level, 'complete': complete}
    component = {'Wind thresholds':'wind','Rain thresholds':'rain','Snow thresholds':'snow'}.get(area)
    if component:
        expected['conditions'] = {component:level}
    add(identifier, area, category, sample, 'Run this case with the isolated command.',
        f'{level}; complete={str(complete).lower()}.',
        {'kind': 'risk', 'weather': weather, 'load': load, 'expect': expected}, 'P0')


# Browser cases use fresh departures and real providers; distances/weather are not fixed assertions.
for suffix, sample, steps, expected in [
    ('01', 'Backend http://127.0.0.1:8000/api/health/', 'Open the URL.', 'HTTP 200; status ok; routing_configured true; demo_mode false.'),
    ('02', 'Frontend http://127.0.0.1:5173', 'Open the app with both terminals running.', 'Routing service ready; no setup banner; usable form and basemap.'),
    ('03', 'Dallas, TX → Austin, TX; departure +1h; 35,000 lb; 25 mi', 'Calculate; inspect resolved city labels and results.', '1–3 real distinct routes, honest warnings if fewer, weather coverage and recommendation or an explicit safety exclusion.'),
    ('04', 'Dallas, TX → Austin, TX; 10,000 lb; 10 mi', 'Calculate once; inspect first and last checkpoints.', '10-mi spacing, origin and destination included, final partial segment handled.'),
    ('05', 'Dallas, TX → Austin, TX; 10,000 lb; 50 mi', 'Calculate; compare checkpoint density with SMK-04.', 'Fewer checkpoints, 50-mi spacing; never count checkpoints as hazardous miles.'),
    ('06', 'Dallas, TX → Irving, TX; 10,000 lb; 50 mi', 'Calculate a short trip.', 'For a returned trip shorter than 50 mi: only origin and destination; otherwise follow actual distance.'),
    ('07', 'New York, NY → Boston, MA; 30,000 lb; 25 mi', 'Calculate; inspect timezone-labelled ETAs.', 'Real provider geometry and weather, or a clear provider restriction/error; no fixed route count assumption.'),
    ('08', 'Toronto, ON, Canada → Ottawa, ON, Canada; 10,000 lb; 50 mi', 'Calculate; inspect distance/weather units.', 'Miles, mph, inches and pounds remain consistent outside the US; disclose provider limitations.'),
]:
    add('SMK-'+suffix, 'Startup and normal trips', 'Regular', sample, steps, expected, priority='P0')

for suffix, sample, steps, expected in [
    ('01', 'Origin empty', 'Clear Origin and submit.', 'Required-field validation; no calculation request.'),
    ('02', 'Destination empty', 'Clear Destination and submit.', 'Required-field validation; no calculation request.'),
    ('03', 'Origin spaces only', 'Enter spaces in Origin and submit.', 'Useful validation; never treat blank text as a location.'),
    ('04', 'Both fields Dallas, TX', 'Use the same origin and destination.', 'Rejected; user can correct and retry.'),
    ('05', 'Origin Dallas, TX; destination dallas, tx', 'Submit case-only duplicate locations.', 'Rejected as the same location.'),
    ('06', 'Origin and destination both " Dallas, TX "', 'Include surrounding spaces and submit.', 'Trimmed duplicates rejected.'),
    ('07', 'Dallas, Texas → Dallas, TX', 'Submit aliases that may resolve to identical coordinates.', 'If coordinates are identical, reject; if provider resolves different points, show those exact points.'),
    ('08', 'Origin A', 'Enter one character and submit.', 'Minimum two-character validation.'),
    ('09', 'Origin "A" repeated 201 times', 'Paste into the input.', 'Field caps at 200 characters; never allows an oversized request silently.'),
    ('10', 'Type Aust then Austin rapidly', 'Inspect suggestions after pausing about 0.5 seconds.', 'Debounced matching suggestions; obsolete responses do not replace the latest location.'),
    ('11', 'A suggestion for Austin, TX', 'Select a suggestion; submit a trip.', 'Selected label remains in the field and backend resolves the intended location.'),
    ('12', 'Dallas, TX ↔ Austin, TX', 'Click the swap button.', 'Both fields swap once; no calculation starts automatically.'),
    ('13', 'Paris, TX versus Paris, France', 'Enter each with region/country; inspect labels before calculation.', 'Resolved city/country is visible; do not silently assume an ambiguous city is the intended one.'),
    ('14', 'Montréal, QC, Canada → Ottawa, ON, Canada', 'Enter accented city text.', 'Unicode text works or returns a clear provider limitation; no encoding corruption.'),
    ('15', 'qzxv-no-such-place-999999', 'Try as Origin; inspect the actual geocoding result.', 'Clear no-location error if none; if fuzzy matching resolves somewhere, record the label instead of assuming gibberish guarantees no result.'),
    ('16', '<img src=x onerror=alert(1)>', 'Enter as a location and try submission.', 'Displayed as inert text or rejected; no JavaScript execution. Provider match/error may vary.'),
]:
    add('LOC-'+suffix, 'Location entry', 'Validation' if suffix not in ('10','11','12','13','14') else 'Interaction', sample, steps, expected)


def validation_case(identifier, area, sample, changes=None, valid=False, omit=(), departure_offset=None, expected_fields=None):
    spec = {'kind': 'serializer', 'changes': changes or {}, 'omit': list(omit), 'expect': {'valid': valid}}
    if departure_offset is not None:
        spec['departure_offset'] = departure_offset
    if expected_fields:
        spec['expect'].update(expected_fields)
    add(identifier, area, 'Validation', sample, 'Run this isolated serializer check; it does not call providers.',
        'Accepted by validation; routing availability is a separate check.' if valid else 'Rejected with validation errors, not an unhandled exception.', spec)

for index, sample, changes, valid, omit in [
    (1, 'Omit origin', {}, False, ['origin']), (2, 'Omit destination', {}, False, ['destination']),
    (3, 'Origin null', {'origin': None}, False, []), (4, 'Origin 201 characters', {'origin': 'A'*201}, False, []),
    (5, 'Origin exactly 200 characters', {'origin': 'A'*200}, True, []),
    (6, 'Whitespace around valid locations', {'origin': ' Dallas, TX ', 'destination': ' Austin, TX '}, True, []),
    (7, 'Case-insensitive duplicate locations', {'destination': 'DALLAS, TX'}, False, []),
    (8, 'Unsupported interval 20', {'interval_miles': 20}, False, []),
    (9, 'Omit interval', {}, True, ['interval_miles']),
    (10, 'Interval null', {'interval_miles': None}, False, []),
]:
    validation_case(f'VAL-{index:02}', 'API field validation', sample, changes, valid, omit,
                    expected_fields={'interval_miles': 25} if index == 9 else None)

for index, value, valid in [(1,0,False),(2,-1,False),(3,0.009,False),(4,0.01,True),(5,1,True),
                            (6,29999.99,True),(7,30000,True),(8,30000.01,True),(9,40000,True),
                            (10,40000.01,True),(11,200000,True),(12,200000.01,False),
                            (13,'abc',False),(14,'NaN',False),(15,'Infinity',False),(16,None,False)]:
    validation_case(f'INP-{index:02}', 'Load input limits', f'Cargo {value!r} lb', {'load_weight_lb': value}, valid)
validation_case('INP-17', 'Load input limits', 'Omit load weight', omit=['load_weight_lb'])
validation_case('INP-18', 'Load input limits', 'Boolean true is not a cargo-weight number', {'load_weight_lb': True})

for suffix, sample, steps, expected in [
    ('01','Departure empty','Clear date/time and submit.','Required validation; no calculation.'),
    ('02','Departure 1 minute ago','Choose a past local time and submit.','UI rejects a past departure; the API has a documented five-minute clock-skew allowance.'),
    ('03','Departure tomorrow at 00:30','Calculate and inspect checkpoint ETAs.','No incorrect day reset when the trip crosses midnight.'),
    ('04','Device timezone Asia/Karachi','Inspect the form label and checkpoint times.','Device timezone is explicit; UTC instants are converted consistently.'),
    ('05','Departure today +16 days','Submit a trip.','Backend rejects a departure beyond 15 days; display validation message.'),
    ('06','Departure +15 days, slider +48h','If a route is returned, inspect coverage and move slider.','Times outside actual returned forecasts are Unknown/unavailable; no fabricated weather or Low fallback.'),
]:
    add('TIME-'+suffix, 'Departure and timezones', 'Boundary', sample, steps, expected)
for identifier, sample, seconds, valid in [('DATE-01','Frozen NOW minus 301 seconds',-301,False),
 ('DATE-02','Frozen NOW minus exactly 300 seconds',-300,True),('DATE-03','Frozen NOW minus 299 seconds',-299,True),
 ('DATE-04','Frozen NOW',0,True),('DATE-05','Frozen NOW plus exactly 15 days',15*86400,True),
 ('DATE-06','Frozen NOW plus 15 days and 1 second',15*86400+1,False)]:
    validation_case(identifier,'Date validation boundaries',sample,valid=valid,departure_offset=seconds)
validation_case('DATE-07','Date validation boundaries','Naive timestamp 2026-11-06T13:00:00',{'departure_at':'2026-11-06T13:00:00'})
validation_case('DATE-08','Date validation boundaries','Invalid timestamp text',{'departure_at':'not-a-date'})
validation_case('DATE-09','Date validation boundaries','Impossible calendar date 2026-02-30T12:00:00Z',{'departure_at':'2026-02-30T12:00:00Z'})
validation_case('DATE-10','Date validation boundaries','Omit departure',omit=['departure_at'])
validation_case('DATE-11','Date validation boundaries','2026-11-06T18:00:00+05:00 equals 13:00Z',
                {'departure_at':'2026-11-06T18:00:00+05:00'},True,expected_fields={'departure_at':'2026-11-06T13:00:00+00:00'})
add('DATE-12','Date validation boundaries','Special','Repeated New York hour: 2026-11-01T01:30:00-04:00 and -05:00',
    'Run the frozen-clock DST check.','Both explicit offsets accepted; their UTC instants differ by 3,600 seconds.',
    {'kind':'dst','expect':{'valid':True,'difference_seconds':3600}},'P0')

wind_cases = [(0,'Low'),(24.99,'Low'),(25,'Moderate'),(25.01,'Moderate'),(34.99,'Moderate'),
              (35,'High'),(35.01,'High'),(44.99,'High'),(45,'Severe'),(45.01,'Severe'),(54.99,'Severe'),(55,'No Travel'),(55.01,'No Travel')]
rain_cases = [(0,'Low'),(0.099,'Low'),(0.10,'Moderate'),(0.101,'Moderate'),(0.249,'Moderate'),(0.25,'High'),
              (0.251,'High'),(0.499,'High'),(0.50,'Severe'),(0.501,'Severe'),(0.999,'Severe'),(1.00,'Severe'),(1.001,'No Travel')]
snow_cases = [(0,'Low'),(0.499,'Low'),(0.50,'Moderate'),(0.501,'Moderate'),(0.999,'Moderate'),(1.00,'High'),
              (1.001,'High'),(1.999,'High'),(2.00,'Severe'),(2.001,'Severe'),(2.999,'Severe'),(3.00,'Severe'),(3.001,'No Travel')]
for prefix, area, values, field, unit in [('WND','Wind thresholds',wind_cases,'wind','mph'),
                                       ('RAN','Rain thresholds',rain_cases,'rain','in/hr'),('SNW','Snow thresholds',snow_cases,'snow','in/hr')]:
    for index,(value,level) in enumerate(values,1):
        risk_case(f'{prefix}-{index:02}',area,f'{field.capitalize()} {value} {unit}; other weather 0; cargo 10,000 lb',level=level,**{field:value})

for index,(wind,load,level) in enumerate([
 (50,29999.99,'Severe'),(50,30000,'Severe'),(50,30000.01,'No Travel'),(50,30001,'No Travel'),
 (40,39999.99,'High'),(40,40000,'High'),(40,40000.01,'Severe'),(40,40001,'Severe'),
 (35,40001,'Severe'),(44.99,40001,'Severe'),(45,30000,'Severe'),(45,30001,'No Travel'),
 (54.99,30001,'No Travel'),(55,0.01,'No Travel'),(55,30000,'No Travel'),(55,200000,'No Travel'),(34.99,200000,'Moderate')],1):
    risk_case(f'LDR-{index:02}','Cargo wind overrides',f'Wind {wind} mph; cargo {load} lb; rain/snow 0',wind=wind,load=load,level=level)

for index,(wind,rain,snow,load,level) in enumerate([
 (25,0.25,0,10000,'High'),(35,0.1,2,10000,'Severe'),(40,1.01,0,45000,'No Travel'),
 (0,0,3.01,10000,'No Travel'),(0,0,0,35000,'Low'),(55,0.5,0,10000,'No Travel'),
 (40,0,1,45000,'Severe'),(45,0.1,0.5,35000,'No Travel'),(10,1,0,35000,'Severe'),(10,0,3,35000,'Severe')],1):
    risk_case(f'MIX-{index:02}','Combined weather',f'Wind {wind}; rain {rain}; snow {snow}; cargo {load} lb',
              wind=wind,rain=rain,snow=snow,load=load,level=level,category='Combination')
for index,(field,value) in enumerate([('wind',None),('rain',None),('snow',None),('wind',-1),('rain',-0.1),('snow',-0.1),
                                     ('wind','bad'),('wind','$nan'),('wind','$inf'),('wind',True)],1):
    risk_case(f'MIS-{index:02}','Missing and invalid weather',f'{field}={value!r}; other weather 0',
              level='Unknown',complete=False,category='Negative',**{field:value})
risk_case('MIS-11','Missing and invalid weather','Wind 55; rain missing; snow 0',wind=55,rain=None,level='No Travel',complete=False,category='Safety')
risk_case('MIS-12','Missing and invalid weather','Wind missing; rain 1.01; snow 0',wind=None,rain=1.01,level='No Travel',complete=False,category='Safety')
add('MIS-13','Missing and invalid weather','Negative','Entire weather object is missing','Run the controlled check.',
    'Unknown; incomplete; never Low.',{'kind':'risk','weather':None,'load':35000,'expect':{'level':'Unknown','complete':False}},'P0')
risk_case('MIS-14','Missing and invalid weather','Boolean false wind must not become numeric zero',wind=False,level='Unknown',complete=False,category='Negative')
risk_case('MIS-15','Missing and invalid weather','String rain "0.10" is invalid provider data',rain='0.10',level='Unknown',complete=False,category='Negative')

for suffix,miles,interval,expected in [
 ('01',117,10,[0,10,20,30,40,50,60,70,80,90,100,110,117]),
 ('02',117,25,[0,25,50,75,100,117]),('03',117,50,[0,50,100,117]),
 ('04',50,25,[0,25,50]),('05',7,25,[0,7]),('06',25.01,25,[0,25,25.01])]:
    add('GEO-'+suffix,'Checkpoints and ETAs','Boundary',f'{miles} miles; {interval}-mi interval',
        'Run the synthetic road-geometry calculation.',f'Checkpoint miles exactly {expected}; origin/destination included.',
        {'kind':'geometry','miles':miles,'interval':interval,'expect':{'distances':expected,'checkpoint_count':len(expected),'vertices_preserved':True}},'P0')
add('GEO-07','Checkpoints and ETAs','Regular','117 miles; 25-mi interval; total duration 11,700 seconds',
    'Inspect second checkpoint ETA offset.','Mile 25 arrives 2,500 seconds after departure; destination offset 11,700 seconds.',
    {'kind':'geometry','miles':117,'interval':25,'expect':{'second_eta_seconds':2500,'arrival_seconds':11700}},'P0')
add('GEO-08','Checkpoints and ETAs','Special','Start 2026-11-06 23:00 UTC; duration 11,700 seconds',
    'Inspect destination timestamp.','Arrival 2026-11-07T02:15:00+00:00.',
    {'kind':'geometry','miles':117,'interval':25,'expect':{'arrival_at':'2026-11-07T02:15:00+00:00'}})
add('GEO-09','Checkpoints and ETAs','Special','Road bends through [1,0] before [1,1]',
    'Inspect a checkpoint at 75% distance and preserved road vertices.','Longitude near 1 at 75%; slices retain the bend, not a straight origin/destination shortcut.',
    {'kind':'geometry','miles':117,'interval':25,'expect':{'longitude_at_75_percent':1,'vertices_preserved':True}},'P0')
add('GEO-10','Checkpoints and ETAs','Special','Geometry [179,10] → [-179,10]',
    'Run antimeridian interpolation.','Midpoint absolute longitude near 180, not 0.',{'kind':'antimeridian','expect':{'midpoint_absolute_longitude':180}})
for suffix,changes,exception in [('11',{'coordinates':[]},'ProviderError'),('12',{'coordinates':[[0,0],[0,0]]},'ProviderError'),
 ('13',{'coordinates':[[181,0],[0,0]]},'ProviderError'),('14',{'miles':0},'ProviderError'),
 ('15',{'duration':0},'ProviderError'),('16',{'interval':20},'ValueError')]:
    add('GEO-'+suffix,'Checkpoints and ETAs','Negative',json.dumps(changes),'Run malformed provider-geometry scenario.',
        'Reject unusable data; no fabricated geometry or ETA.',{'kind':'geometry',**changes,'expect_error':exception},'P0')

summary_cases = [
 ('01',[[0,'Low'],[25,'Low'],[50,'High'],[67,'Severe']],{'risk_miles':{'Low':25,'High':25,'Severe':17},'average_risk':101/67,'coverage_percent':100,'eligible':True},'25 Low mi + 25 High mi + 17 Severe mi; average 101/67.'),
 ('02',[[0,'Low'],[25,'High'],[50,'Low']],{'risk_miles':{'High':50},'average_risk':2},'Both intervals take the High endpoint; 50 High miles.'),
 ('03',[[0,'Low'],[25,'Unknown',False],[50,'Low']],{'risk_miles':{'Unknown':50},'average_risk':None,'eligible':False,'coverage_percent':0},'50 Unknown miles; average null; ineligible.'),
 ('04',[[0,'Low'],[25,'Low'],[50,'Unknown',False]],{'risk_miles':{'Low':25,'Unknown':25},'coverage_percent':50,'average_risk':None},'Coverage 50%; average null, not a safe-looking partial average.'),
 ('05',[[0,'Low'],[25,'No Travel']],{'risk_miles':{'No Travel':25},'blocked':True,'eligible':False},'25 No Travel miles; excluded.'),
 ('06',[[0,'Unknown',False],[25,'No Travel']],{'risk_miles':{'No Travel':25},'complete':False,'blocked':True,'eligible':False},'Known No Travel preserved despite missing adjacent weather.'),
 ('07',[[0,'Low'],[7,'Severe']],{'risk_miles':{'Severe':7},'average_risk':3},'Final partial segment contributes 7 miles, not a full 25.'),
 ('08',[[0,'Low'],[25,'Low']],{'eligible':False,'complete':True},'Complete weather but unsupported truck mode remains ineligible.'),
]
for suffix,points,expect,description in summary_cases:
    add('SUM-'+suffix,'Distance-weighted summaries','Calculation',str(points),'Run the endpoint-to-segment calculation.',description,
        {'kind':'summary','points':points,'truck_supported':suffix!='08','expect':expect},'P0')
for suffix,interval in [('09',10),('10',25),('11',50)]:
    add('SUM-'+suffix,'Distance-weighted summaries','Consistency',f'117 miles; uniform High risk; interval {interval}',
        'Run uniform-risk summary at this interval.','117 High miles; average 2; total miles remain 117.',
        {'kind':'uniform_summary','interval':interval,'expect':{'risk_miles':{'High':117},'average_risk':2,'total_miles':117}},'P0')

ranking_cases = [
 ('01',[{'id':'A','severe':1,'high':90,'average':2,'duration':9000},{'id':'B','severe':2,'duration':100}], 'A','Fewer Severe miles wins even with more High miles and longer duration.'),
 ('02',[{'id':'A','high':1,'average':2,'duration':9000},{'id':'B','high':2,'average':1,'duration':100}], 'A','With equal Severe miles, fewer High miles wins.'),
 ('03',[{'id':'A','average':0.5,'duration':9000},{'id':'B','average':1,'duration':100}], 'A','Equal Severe/High miles: lower average wins.'),
 ('04',[{'id':'A','duration':500},{'id':'B','duration':600}], 'A','Equal risk metrics: shorter duration wins.'),
 ('05',[{'id':'B'},{'id':'A'}], 'A','Exact tie breaks deterministically by route ID.'),
 ('06',[{'id':'unsafe','eligible':False,'blocked':True},{'id':'safe','severe':20}], 'safe','No Travel route cannot win by having fewer Severe miles.'),
 ('07',[{'id':'unknown','eligible':False},{'id':'safe','high':50}], 'safe','Incomplete weather cannot beat a fully covered route.'),
 ('08',[{'id':'A','eligible':False,'blocked':True},{'id':'B','eligible':False,'blocked':True}], None,'No safe route available; do not recommend a least-bad unsafe route.'),
 ('09',[{'id':'A','eligible':False},{'id':'B','eligible':False,'blocked':True}], None,'Mixed incomplete/unsafe options also yield no recommendation.'),
 ('10',[{'id':'only'}], 'only','One eligible route can be recommended; no need to invent alternatives.'),
]
for suffix,routes,expected,description in ranking_cases:
    add('RNK-'+suffix,'Recommendation order','Safety',json.dumps(routes),'Run the ranking scenario.',description,
        {'kind':'ranking','routes':routes,'expect':{'recommended':expected}},'P0')

for suffix,variant,expected,description in [
 ('01','one',{'route_count':1},'One actual option plus a fewer-alternatives warning.'),
 ('02','two',{'route_count':2},'Two distinct options, no fake third route.'),
 ('03','three',{'route_count':3,'max_alternatives':2,'travel_mode':'truck'},'Main route plus two alternatives, requested in truck mode.'),
 ('04','duplicate',{'route_count':1,'duplicate_warning':True},'Identical alternatives deduplicated.'),
 ('05','empty',{'error_code':'no_routes','error_status':422},'No-route error; no risk calculations on invented geometry.'),
 ('06','invalid_geometry',{'error_code':'no_routes','error_status':422},'Unusable route omitted; no usable routes remain.'),
 ('07','invalid_duration',{'error_code':'no_routes','error_status':422},'Missing/zero ETA route omitted.'),
 ('08','mixed_invalid',{'route_count':1},'Keep usable route and explain omitted malformed alternative.'),
 ('09','nontruck',{'route_count':1,'truck_supported':[False]},'Non-truck section disclosed; downstream eligibility must be false.'),
 ('10','three',{'vehicle_weight_kg':21773},'30,000 lb cargo + 18,000 lb empty weight converts upward to 21,773 kg.'),
]:
    add('RTE-'+suffix,'Routing provider alternatives','Provider',variant,'Run the isolated TomTom-response scenario.',description,
        {'kind':'routing','variant':variant,'expect':expected},'P0')
add('RTE-11','Routing provider alternatives','Negative','Origin and destination resolve to identical coordinates',
    'Run same-coordinate routing guard.','422 same_location before a routing request.',
    {'kind':'routing','variant':'same_location','expect':{'error_code':'same_location','error_status':422}},'P0')
for suffix,variant,expected,description in [
 ('01','valid',{'place_count':1,'coordinates':[-96.8,32.8]},'Human-readable address resolves to GeoJSON longitude/latitude order.'),
 ('02','empty',{'error_code':'location_not_found','error_status':422},'No geocoding results produce a clear 422.'),
 ('03','invalid_position',{'error_code':'location_not_found','error_status':422},'Out-of-range latitude is not used in routing.'),
 ('04','malformed',{'error_status':502},'Malformed geocoder coordinates produce a provider error.'),
 ('05','cache',{'place_count':1,'provider_calls':1},'Repeated equivalent search uses cached provider results.'),
 ('06','encoded',{'encoded_query':True},'Slash, question mark, and angle brackets are encoded as query text, not API path/query injection.'),
]:
    add('GCD-'+suffix,'Geocoding response handling','Provider',variant,'Run the isolated geocoder response.',description,
        {'kind':'geocoding','variant':variant,'expect':expected},'P0')

for suffix,variant,expected,description in [
 ('01','metric',{'wind_mph':50,'rain_in_per_hour':0.2,'snow_in_per_hour':1},'80.4672 km/h → 50 mph; 2.54 mm rain + 2.54 mm showers → 0.2 in; 2.54 cm snow → 1 in.'),
 ('02','imperial',{'wind_mph':25,'rain_in_per_hour':0.25,'snow_in_per_hour':0.5},'Imperial values preserved; rainfall includes showers.'),
 ('03','missing_snow',{'snow_in_per_hour':None},'Missing snowfall stays null, not zero.'),
 ('04','negative_rain',{'rain_in_per_hour':None},'Negative provider rain becomes unavailable.'),
 ('05','unknown_unit',{'error_status':502},'Unsupported snowfall unit rejected.'),
 ('06','irregular_time',{'error_status':502},'Irregular hourly timeline rejected.'),
 ('07','mismatched_length',{'error_status':502},'Misaligned arrays rejected.'),
]:
    add('WTH-'+suffix,'Weather normalization','Provider',description,'Run the controlled normalization scenario.',description,
        {'kind':'normalization','variant':variant,'expect':expected},'P0')
for suffix,offset,expected in [('08',0,10),('09',1,30),('10',3600,30),('11',3601,55),('12',-1,None),('13',7201,None)]:
    add('WTH-'+suffix,'Weather normalization','Time boundary',f'Hourly winds [10,30,55]; target offset {offset} seconds',
        'Run timestamp selection.','Unavailable outside the horizon.' if expected is None else f'Select wind {expected} mph from the interval ending at/after the target time.',
        {'kind':'weather_at','offset':offset,'expect':{'wind_mph':expected}},'P0')
for suffix,variant,expected,description in [
 ('14','deduplicate',{'unique_locations':2,'provider_calls':1,'missing':0},'Repeated coordinates reuse one request/cache entry.'),
 ('15','batch',{'unique_locations':51,'provider_calls':3,'missing':0},'51 coordinates are requested in three batches of at most 25.'),
 ('16','failure',{'missing':2,'warning':True},'Provider failure yields unavailable weather and warnings.'),
 ('17','wrong_count',{'missing':2,'warning':True},'Wrong number of provider locations is not silently assigned to checkpoints.'),
 ('18','limit',{'error_status':422,'error_code':'sampling_limit'},'Over-limit sample counts return an explicit sampling-limit error.'),
]:
    add('WTH-'+suffix,'Weather normalization','Performance',variant,'Run the batched/cache scenario.',description,
        {'kind':'weather_batch','variant':variant,'expect':expected})
for suffix,variant,expected,description in [
 ('19','meters_per_second',{'wind_mph':22.369362921},'10 m/s is normalized to approximately 22.3694 mph.'),
 ('20','knots',{'wind_mph':11.50779448},'10 knots is normalized to approximately 11.5078 mph.'),
 ('21','snow_mm',{'snow_in_per_hour':1},'25.4 mm snowfall depth is normalized to 1 inch.'),
 ('22','empty_time',{'error_status':502},'An empty forecast timeline is unavailable, not safe weather.'),
 ('23','iso_time',{'error_status':502},'Unexpected non-Unix time metadata is rejected.'),
 ('24','missing_variable',{'error_status':502},'A missing required hourly variable is rejected.'),
]:
    add('WTH-'+suffix,'Weather normalization','Provider',description,'Run isolated unit/schema handling.',description,
        {'kind':'normalization','variant':variant,'expect':expected},'P0')

for suffix,variant,expected in [('01','timeout',504),('02','connection',502),('03','rate_limit',429),
                               ('04','unauthorized',503),('05','forbidden',503),('06','server_error',502),
                               ('07','invalid_json',502),('08','invalid_shape',502)]:
    add('ERR-'+suffix,'Provider transport failures','Negative',variant,'Simulate only this provider failure; no real API request.',
        f'Friendly structured error; HTTP-equivalent status {expected}; no key or raw request URL exposed.',
        {'kind':'transport','variant':variant,'expect':{'error_status':expected,'secret_exposed':False}},'P0')

for suffix,variant,expected,description in [
 ('01','safe',{'route_count':3,'recommended':'route-1','all_complete':True},'Three eligible routes and a deterministic recommendation.'),
 ('02','unsafe',{'recommended':None,'all_blocked':True},'All routes No Travel; no recommendation.'),
 ('03','missing',{'recommended':None,'all_complete':False},'Missing weather cannot become Low or a safe recommendation.'),
 ('04','nontruck',{'recommended':None,'all_eligible':False},'A returned non-truck section prevents a recommendation.'),
 ('05','slider',{'recommended':'route-1','arrival_risk':'Low','forecast48_risk':'No Travel','recommendation_unchanged':True},'Slider +48h changes selected-hour weather while route arrival risk/recommendation stays unchanged.'),
 ('06','horizon',{'recommended':None,'all_complete':False},'Arrival outside forecast timestamps stays incomplete.'),
]:
    add('FLOW-'+suffix,'Complete controlled pipeline','Integration',variant,'Run the isolated route/weather pipeline.',description,
        {'kind':'pipeline','variant':variant,'expect':expected},'P0')

for suffix,method,path,params,status in [('01','get','/api/health/',{},200),
 ('02','get','/api/routes/calculate/',{},405),('03','post','/api/health/',{},405),
 ('04','get','/api/places/',{'q':'A'},400),('05','get','/api/places/',{'q':'A'*201},400),
 ('06','get','/api/trips/00000000-0000-0000-0000-000000000000/',{},404),
 ('07','get','/api/trips/not-a-uuid/',{},404),
 ('08','get','/api/trips/00000000-0000-0000-0000-000000000000/forecast/',{'hour':-1},400),
 ('09','get','/api/trips/00000000-0000-0000-0000-000000000000/forecast/',{'hour':49},400),
 ('10','get','/api/trips/00000000-0000-0000-0000-000000000000/forecast/',{'hour':'1.5'},400),
 ('11','get','/api/trips/00000000-0000-0000-0000-000000000000/forecast/',{'hour':'abc'},400)]:
    add('API-'+suffix,'HTTP API contract','Negative' if status>=400 else 'Regular',f'{method.upper()} {path}; {params}',
        'Run this isolated HTTP-handler check.',f'HTTP {status}; JSON response for registered API endpoints.' if suffix!='07' else 'HTTP 404 for the unmatched UUID URL; the default HTML 404 is acceptable.',
        {'kind':'api','method':method,'path':path,'params':params,'expect':{'http_status':status}})
add('API-12','HTTP API contract','Negative','POST incomplete JSON {origin: Dallas, TX}','Run handler validation.',
    'HTTP 400 with required field errors.',{'kind':'api','method':'post','path':'/api/routes/calculate/','params':{'origin':'Dallas, TX'},'expect':{'http_status':400}})
add('API-13','HTTP API contract','Negative','Valid trip, but key absent in isolated settings','Run the missing-key handler scenario.',
    'HTTP 503; error code missing_api_key.',{'kind':'api','variant':'missing_key','expect':{'http_status':503,'error_code':'missing_api_key'}},'P0')
add('API-14','HTTP API contract','Negative','Malformed JSON body','Run malformed JSON submission.',
    'HTTP 400, no uncaught server error.',{'kind':'api','variant':'bad_json','expect':{'http_status':400}})
for suffix,hour in [('15',0),('16',48),('17',None)]:
    add('API-'+suffix,'HTTP API contract','Boundary',f'Seeded isolated trip; forecast hour {hour if hour is not None else "omitted"}',
        'Request selected-hour forecast from a process-local test trip.',f'HTTP 200; returned hour {hour if hour is not None else 0}.',
        {'kind':'api','variant':'seeded','hour':hour,'expect':{'http_status':200,'hour':hour if hour is not None else 0}})
add('API-18','HTTP API contract','Negative','Isolated anonymous throttle reduced to one request/hour',
    'Make two isolated mocked location searches; do not flood the real server.','First HTTP 200, second HTTP 429.',
    {'kind':'api','variant':'throttle','expect':{'http_status':429,'first_status':200}})
add('API-19','HTTP API contract','Negative','POST text/plain to the JSON route endpoint',
    'Run unsupported content-type handler check.','HTTP 415 with a clear unsupported-media response.',
    {'kind':'api','variant':'bad_content_type','expect':{'http_status':415}})
add('API-20','HTTP API contract','Boundary','Forecast hour empty string; parameter is present',
    'Run isolated query validation.','HTTP 400; an omitted hour defaults to 0 but an empty explicit hour is invalid.',
    {'kind':'api','method':'get','path':'/api/trips/00000000-0000-0000-0000-000000000000/forecast/','params':{'hour':''},'expect':{'http_status':400}})

for suffix,sample,steps,expected in [
 ('01','Baseline calculated trip','Select each route card.','Selected card, checkpoint table, and highlighted road geometry correspond to the same route.'),
 ('02','Baseline calculated trip','Click a checkpoint on the map.','Panel shows coordinates, mile distance, arrival time, wind, rain, snow, risk and reason.'),
 ('03','Baseline calculated trip','Open Origin, an interior checkpoint, and Destination from the table.','Correct distinct checkpoint details and map position for each.'),
 ('04','Baseline calculated trip','Close checkpoint panel.','Panel closes; map and route selection remain usable.'),
 ('05','Baseline calculated trip','Pan/zoom, then click Fit all routes.','All available alternatives fit; no page freeze or route disappearance.'),
 ('06','Baseline calculated trip','Zoom into bends and compare routes/checkpoints with roads.','Full provider geometry follows roads; no straight-line fabricated routes.'),
 ('07','Baseline calculated trip','Inspect legend, road colors, and checkpoint badges.','Text labels accompany colors; road colors describe arrival-time risk.'),
 ('08','Baseline calculated trip','Inspect each risk bar and detailed summary.','Low+Moderate+High+Severe+No Travel+Unknown miles equal total distance within rounding tolerance.'),
 ('09','Baseline calculated trip','Compare ETA at origin, interior points, destination, and route card.','ETAs increase; destination ETA matches route summary; dates/timezone are explicit.'),
 ('10','Browser width 390 px','Inspect form, cards, map, details and table.','No horizontal page overflow; table itself may scroll horizontally; controls remain accessible.'),
 ('11','Browser width 768 px','Resize from desktop to tablet.','Map resizes correctly; no overlapping or offscreen primary controls.'),
 ('12','Browser width 1440 px','Inspect three routes when actually available.','Readable cards; map retains useful area; labels and metrics are not clipped.'),
 ('13','Keyboard only','Tab through form, interval buttons, calculate, cards and checkpoint table.','Visible focus; primary actions work with Enter/Space; record inaccessible controls as failures.'),
 ('14','Risk rules dialog','Open rules, inspect values, close it; try Escape and keyboard focus.','Displayed rules match thresholds. Escape/focus should support an accessible dialog; record any unsupported behavior rather than skipping it.'),
 ('15','Zoom browser to 200%','Inspect controls and details.','Readable content, usable scrolling, no loss of essential actions.'),
 ('16','Console and Network panels','Perform one normal calculation and inspect errors.','No uncaught page errors or exposed API keys; provider failures appear as clear app messages.'),
]:
    add('MAP-'+suffix,'Map and responsive interface','Interaction',sample,steps,expected)
add('MAP-17','Map and responsive interface','Boundary','Viewport 360 px wide','Inspect form, results, map and details at this width.',
    'No horizontal page overflow; essential controls remain usable.')
add('MAP-18','Map and responsive interface','Boundary','Viewport 320 px wide','Inspect a small-phone layout and try primary controls.',
    'No horizontal page overflow or lost primary controls; record any current minimum-width limitation as a failure.')

for suffix,sample,steps,expected in [
 ('01','Before any trip','Try the slider.','Slider disabled; no meaningless forecast requests.'),
 ('02','Baseline trip; offset 0','Move to the left endpoint.','Timestamp equals departure; forecast response hour=0.'),
 ('03','Baseline trip; offset 48','Move to the right endpoint.','Timestamp equals departure plus 48 hours; response hour=48.'),
 ('04','Offsets 1, 12, 24, 36','Visit each offset and inspect forecast request/timestamp.','Each returned hour and displayed timestamp matches the selection.'),
 ('05','Same checkpoint at 0 then 48','Compare arrival and corridor sections.','Corridor weather reflects selected time; arrival weather remains fixed. Similar real weather at different hours is valid.'),
 ('06','Recommended trip','Move through several hours.','Recommendation and arrival-risk road segments do not rerank/change because of the slider.'),
 ('07','Weather layer toggle','Toggle off then on.','Corridor heat layer changes visibility; route lines/checkpoints remain visible.'),
 ('08','Slow 3G network; rapidly scrub 0→12→48','Inspect last forecast response and caption.','Final +48h data wins; stale earlier requests cannot overwrite it.'),
 ('09','Visit 12, then 24, then 12','Inspect Network panel.','Second visit to 12 uses client cache; no duplicate request for that cached hour.'),
 ('10','Slow network, uncached hour','Move slider and watch loading state.','Do not display previous-hour weather as if it matched the new label; show loading/unavailable state.'),
 ('11','Backend stopped temporarily after trip','Move to an uncached hour; restore backend and retry.','Clear forecast error; retry action works, or trip-expired message requests recalculation after restart.'),
 ('12','A forecast beyond provider horizon','Inspect missing count and checkpoint selected-hour section.','Unknown/unavailable labels; no invented Low-risk heatmap.'),
 ('13','Calculated trip','Toggle layer repeatedly and inspect map smoothness.','No accumulating map instances, duplicate controls, or frozen interaction.'),
 ('14','Trip A, then calculate Trip B','Inspect slider and checkpoint details.','Offset resets to 0; no forecast or checkpoint details from Trip A.'),
]:
    add('SLD-'+suffix,'Forecast slider and corridor','Interaction',sample,steps,expected,priority='P0' if suffix in ('02','03','05','06','08','12') else 'P1')

for suffix,sample,steps,expected in [
 ('01','Backend stopped; frontend stays open','Stop Django with Ctrl+C; return to tab.','Service offline/connection unavailable; no stale claim of readiness.'),
 ('02','Backend restarted with existing valid local key','Restart Django and wait or click Retry connection.','Ready status recovers; trip input text remains intact.'),
 ('03','Setup response false→true in a controlled browser test','Run npm.cmd run test:e2e -- --grep "setup|configuration recheck".','Banner clears automatically or through Check again, without losing draft inputs.'),
 ('04','Slow 3G; valid trip','Submit and immediately click Calculate again.','One active submission; button disabled while working.'),
 ('05','Slow 3G; valid trip','Submit, then Cancel request.','Loading clears; late response cannot populate a cancelled trip. Server may finish an already-started provider call.'),
 ('06','After cancelling','Change destination and calculate.','Only the new trip results appear.'),
 ('07','Map requests blocked in DevTools','Block basemaps.cartocdn.com, reload, inspect after up to 20 seconds.','Map failure/retry feedback; form and route results remain usable. Unblock requests afterward.'),
 ('08','Internet connection temporarily offline','Use DevTools Offline; try an action; restore Online.','Useful connection error; recovery without blank screen.'),
 ('09','An existing calculated trip','Restart Django then request an uncached forecast hour.','404 trip_expired or clear recalculation prompt; no fabricated forecast.'),
 ('10','Configured backend; return to app tab','Switch away and back after backend state changes.','Health rechecked on focus/visibility; display matches current backend.'),
 ('11','Existing safe or unsafe real trip','Recalculate with another load, keeping other inputs similar.','Cargo input is sent correctly; changed outcomes are based on actual wind, not an assumption that higher load always changes risk.'),
]:
    add('REC-'+suffix,'Errors and recovery','Recovery',sample,steps,expected,priority='P0' if suffix in ('01','02','04','05','09') else 'P1')

for suffix,sample,steps,expected in [
 ('01','Dallas, TX → Los Angeles, CA; 10-mi interval','Try one long trip.','Either complete supported analysis or explicit sample-limit/provider error; no silent truncation.'),
 ('02','Same long trip; 50-mi interval','Retry with coarser sampling.','Fewer samples; if still over limit, explain honestly rather than fabricating completion.'),
 ('03','Provider failures or rate limits','Use ERR controlled cases instead of flooding real services.','429/timeout handling proven without exhausting your live account.'),
 ('04','Production Vercel URL','After deployment, repeat SMK-01/02/03 and SLD-03 on HTTPS.','Frontend/API communication and real forecasts work at the actual hosted URL. Mark Blocked until deployed.'),
 ('05','Production environment configuration','Review provider key and Django settings privately in the host dashboard.','Keys server-side; unique production secret; debug false; exact allowed hostname. No secret values copied into results.'),
 ('06','Repository and built frontend','Inspect tracked filenames, browser requests, and JavaScript assets.','No tracked .env/private key; frontend never sends a TomTom private key directly.'),
 ('07','Trip notes','Read sampling, ETA and truck-configuration disclosures.','Uniform-speed/rest-stop limitations and actual configured vehicle restrictions are clear.'),
 ('08','Submission links','Open GitHub, hosted URL and recorded Loom in a separate session.','Evaluator can access all links. Mark Blocked until published/recorded.'),
]:
    add('OPS-'+suffix,'Performance and submission','Operational',sample,steps,expected,priority='P2' if suffix in ('04','05','08') else 'P1')


def expected_subset(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(key in actual and expected_subset(actual[key], value) for key,value in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual)==len(expected) and all(expected_subset(a,b) for a,b in zip(actual,expected))
    if isinstance(expected,(float,int)) and not isinstance(expected,bool):
        return isinstance(actual,(float,int)) and not isinstance(actual,bool) and math.isclose(actual,expected,rel_tol=1e-8,abs_tol=1e-6)
    return actual == expected


def initialize_django():
    sys.path.insert(0,str(ROOT/'backend'))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    import django
    django.setup()


NOW = datetime(2026,11,6,12,tzinfo=timezone.utc)


def baseline():
    return {'origin':'Dallas, TX','destination':'Austin, TX','departure_at':(NOW+timedelta(hours=1)).isoformat(),'load_weight_lb':35000,'interval_miles':25}


def execute(spec):
    from django.core.cache import cache
    from django.test import override_settings
    from services.providers import ProviderError
    from services.risk_engine import calculate_checkpoint_risk, calculate_route_risk
    from services.checkpoints import RouteGeometry, METERS_PER_MILE, generate_checkpoints
    from services.weather import normalize_forecast, weather_at, fetch_forecasts, coordinate_key
    from tests.test_weather import weather_fixture
    from tests.test_api import route_fixture
    from routing.serializers import TripSerializer
    kind = spec['kind']
    if kind == 'risk':
        weather = copy.deepcopy(spec['weather'])
        if weather:
            weather = {key:(float('nan') if value=='$nan' else float('inf') if value=='$inf' else value) for key,value in weather.items()}
        return calculate_checkpoint_risk(weather,spec['load'])
    if kind == 'serializer':
        data = baseline()
        data.update(spec.get('changes',{}))
        if 'departure_offset' in spec:
            data['departure_at'] = (NOW+timedelta(seconds=spec['departure_offset'])).isoformat()
        for field in spec.get('omit',[]): data.pop(field,None)
        with patch('routing.serializers.timezone.now',return_value=NOW):
            serializer = TripSerializer(data=data)
            valid = serializer.is_valid()
        return {'valid':valid,**({'interval_miles':serializer.validated_data['interval_miles'],'departure_at':serializer.validated_data['departure_at'].isoformat()} if valid else {'errors':dict(serializer.errors)})}
    if kind == 'dst':
        values=[]
        with patch('routing.serializers.timezone.now',return_value=datetime(2026,10,31,tzinfo=timezone.utc)):
            for offset in ('-04:00','-05:00'):
                serializer=TripSerializer(data={**baseline(),'departure_at':'2026-11-01T01:30:00'+offset})
                if not serializer.is_valid(): return {'valid':False,'errors':dict(serializer.errors)}
                values.append(serializer.validated_data['departure_at'])
        return {'valid':True,'difference_seconds':(values[1]-values[0]).total_seconds()}
    if kind == 'geometry':
        coordinates=spec.get('coordinates',[[0,0],[1,0],[1,1]])
        geometry=RouteGeometry(coordinates,spec.get('miles',117)*METERS_PER_MILE)
        departure=datetime(2026,11,6,23,tzinfo=timezone.utc)
        points=generate_checkpoints(geometry,spec.get('interval',25),spec.get('duration',11700),departure,'test')
        sliced=geometry.slice(0,geometry.total)
        return {'distances':[p['distance_miles'] for p in points],'checkpoint_count':len(points),
                'vertices_preserved':all(point in sliced for point in coordinates),
                'second_eta_seconds':(datetime.fromisoformat(points[1]['eta'])-departure).total_seconds(),
                'arrival_seconds':(datetime.fromisoformat(points[-1]['eta'])-departure).total_seconds(),
                'arrival_at':points[-1]['eta'],'longitude_at_75_percent':geometry.position(geometry.total*0.75)[0]}
    if kind == 'antimeridian':
        geometry=RouteGeometry([[179,10],[-179,10]],100)
        return {'midpoint_absolute_longitude':abs(geometry.position(50)[0])}
    if kind in ('summary','uniform_summary'):
        points=spec.get('points')
        if kind=='uniform_summary': points=[[d,'High'] for d in [*range(0,117,spec['interval']),117]]
        checkpoints=[{'distance_miles':p[0],'risk':{'level':p[1],'complete':p[2] if len(p)>2 else True}} for p in points]
        result=calculate_route_risk(checkpoints,spec.get('truck_supported',True))
        return {**result,'total_miles':sum(result['risk_miles'].values())}
    if kind == 'ranking':
        from services.recommendation import recommend
        routes=[{'id':r['id'],'duration_seconds':r.get('duration',1000),'summary':{'eligible':r.get('eligible',True),'blocked':r.get('blocked',False),
                 'risk_miles':{'Severe':r.get('severe',0),'High':r.get('high',0)},'average_risk':r.get('average',0)}} for r in spec['routes']]
        identifier,reason=recommend(routes)
        return {'recommended':identifier,'reason':reason}
    if kind == 'routing':
        from services.routing import calculate_routes
        variant=spec['variant']
        raw=route_fixture()
        count=3 if variant=='three' else 2 if variant=='two' else 1
        if variant in ('duplicate','mixed_invalid'): count=2
        raw['routes']=[copy.deepcopy(raw['routes'][0]) for _ in range(count)]
        for index,route in enumerate(raw['routes']):
            if variant!='duplicate': route['legs'][0]['points'][1]['longitude']+=index*0.05
        if variant=='empty': raw['routes']=[]
        if variant=='invalid_geometry': raw['routes'][0]['legs'][0]['points']=[]
        if variant=='invalid_duration': raw['routes'][0]['summary']['travelTimeInSeconds']=0
        if variant=='mixed_invalid': raw['routes'][1]['legs'][0]['points']=[]
        if variant=='nontruck': raw['routes'][0]['sections'][0]['travelMode']='other'
        with override_settings(TOMTOM_API_KEY='controlled-test-key',TRUCK_EMPTY_WEIGHT_LB=18000,TRUCK_DIMENSIONS={}):
            with patch('services.routing.get_json',return_value=raw) as get:
                try:
                    routes,warnings=calculate_routes({'coordinates':[-96,32]},{'coordinates':[-96,32] if variant=='same_location' else [-95.5,32.4]},NOW,30000)
                except ProviderError as error:
                    return {'error_status':error.status,'error_code':error.code}
        params=get.call_args.args[1]
        return {'route_count':len(routes),'truck_supported':[r['truck_supported'] for r in routes],'max_alternatives':params['maxAlternatives'],
                'travel_mode':params['travelMode'],'vehicle_weight_kg':params['vehicleWeight'],'duplicate_warning':any('duplicate' in w for w in warnings)}
    if kind == 'geocoding':
        from services.geocoding import search_places, geocode
        cache.clear()
        variant=spec['variant']
        raw={'results':[{'position':{'lat':32.8,'lon':-96.8},'address':{'freeformAddress':'Dallas, TX'}}]}
        if variant=='empty': raw['results']=[]
        if variant=='invalid_position': raw['results'][0]['position']['lat']=91
        if variant=='malformed': del raw['results'][0]['position']['lat']
        query='Dallas/??<x>' if variant=='encoded' else 'Dallas, TX'
        with override_settings(TOMTOM_API_KEY='controlled-test-key'):
            with patch('services.geocoding.get_json',return_value=raw) as get:
                try:
                    if variant in ('empty','invalid_position','malformed'): geocode(query)
                    places=search_places(query)
                    if variant=='cache': search_places(query.upper())
                except ProviderError as error: return {'error_status':error.status,'error_code':error.code}
        return {'place_count':len(places),'coordinates':places[0]['coordinates'] if places else None,
                'provider_calls':get.call_count,'encoded_query':'Dallas%2F%3F%3F%3Cx%3E.json' in get.call_args.args[0]}
    if kind == 'normalization':
        variant=spec['variant']
        raw=weather_fixture(wind=25,rain=0.10,showers=0.15,snow=0.5)
        if variant=='metric':
            raw=weather_fixture(wind=80.4672,rain=2.54,showers=2.54,snow=2.54)
            raw['hourly_units'].update(wind_speed_10m='km/h',rain='mm',showers='mm',snowfall='cm')
        if variant=='missing_snow': raw['hourly']['snowfall'][0]=None
        if variant=='negative_rain': raw['hourly']['rain'][0]=-1
        if variant=='unknown_unit': raw['hourly_units']['snowfall']='feet'
        if variant=='irregular_time': raw['hourly']['time'][1]+=1
        if variant=='mismatched_length': raw['hourly']['rain'].pop()
        if variant in ('meters_per_second','knots'):
            raw['hourly']['wind_speed_10m']=[10]*385
            raw['hourly_units']['wind_speed_10m']='m/s' if variant=='meters_per_second' else 'kn'
        if variant=='snow_mm':
            raw['hourly']['snowfall']=[25.4]*385
            raw['hourly_units']['snowfall']='mm'
        if variant=='empty_time': raw['hourly']['time']=[]
        if variant=='iso_time': raw['hourly_units']['time']='iso8601'
        if variant=='missing_variable': del raw['hourly']['rain']
        try: return normalize_forecast(raw)['rows'][0]
        except ProviderError as error: return {'error_status':error.status,'error_code':error.code}
    if kind == 'weather_at':
        epoch=int(NOW.timestamp())
        series={'times':[epoch,epoch+3600,epoch+7200],'rows':[{'wind_mph':v} for v in (10,30,55)]}
        row=weather_at(series,NOW+timedelta(seconds=spec['offset']))
        return {'wind_mph':row['wind_mph'] if row else None}
    if kind == 'weather_batch':
        variant=spec['variant']
        coordinates=[[1,2],[1,2],[3,4]] if variant=='deduplicate' else [[1,2],[3,4]]
        if variant=='batch': coordinates=[[index/10,32] for index in range(51)]
        if variant=='limit': coordinates=[[0,1],[1,2],[2,3]]
        cache.clear()
        def response(url,params,provider):
            count=len(params['latitude'].split(','))
            if variant=='failure': raise ProviderError('Simulated weather failure')
            if variant=='wrong_count': return []
            return [weather_fixture() for _ in range(count)] if count>1 else weather_fixture()
        try:
            with override_settings(MAX_WEATHER_LOCATIONS=2 if variant=='limit' else 450):
                with patch('services.weather.get_json',side_effect=response) as get:
                    forecasts,warnings=fetch_forecasts(coordinates)
                    if variant=='deduplicate': fetch_forecasts(coordinates)
                    calls=get.call_count
        except ProviderError as error: return {'error_status':error.status,'error_code':error.code}
        return {'unique_locations':len(forecasts),'provider_calls':calls,'missing':sum(v is None for v in forecasts.values()),'warning':bool(warnings)}
    if kind == 'transport':
        import requests
        from services.providers import get_json
        variant=spec['variant']
        response=Mock(status_code={'rate_limit':429,'unauthorized':401,'forbidden':403,'server_error':500}.get(variant,200))
        response.json.return_value=[] if variant!='invalid_shape' else 'bad root'
        if variant=='invalid_json': response.json.side_effect=ValueError('bad JSON')
        side_effect=requests.Timeout('key=controlled-marker') if variant=='timeout' else requests.ConnectionError('key=controlled-marker') if variant=='connection' else None
        with patch('services.providers.requests.get',return_value=response,side_effect=side_effect):
            try: get_json('https://example.invalid',{'key':'controlled-marker'},'Controlled provider')
            except ProviderError as error:
                return {'error_status':error.status,'error_code':error.code,'secret_exposed':'controlled-marker' in str(error)}
        return {'error_status':None}
    if kind == 'pipeline':
        from services.trips import calculate_trip, forecast_for_trip, get_trip
        variant=spec['variant']
        raw=route_fixture()
        raw['routes']=[copy.deepcopy(raw['routes'][0]) for _ in range(3)]
        for index,route in enumerate(raw['routes']):
            route['legs'][0]['points'][1]['longitude']+=index*0.05
            route['summary']['travelTimeInSeconds']+=index*600
            if variant=='nontruck': route['sections'][0]['travelMode']='other'
        fixture=weather_fixture(wind=55 if variant=='unsafe' else 10,start=int(NOW.timestamp()))
        if variant=='missing': fixture['hourly']['snowfall']=[None]*385
        if variant=='slider': fixture['hourly']['wind_speed_10m'][48:51]=[60,60,60]
        def response(url,params,provider):
            count=len(params['latitude'].split(','))
            return [fixture for _ in range(count)] if count>1 else fixture
        departure=NOW+timedelta(days=20) if variant=='horizon' else NOW+timedelta(hours=1)
        with override_settings(TOMTOM_API_KEY='controlled-test-key'):
            with patch('services.trips.geocode',side_effect=lambda query:{'label':query,'coordinates':[-96,32] if 'Dallas' in query else [-95.5,32.4]}), \
                 patch('services.routing.get_json',return_value=raw), patch('services.weather.get_json',side_effect=response):
                trip=calculate_trip({**baseline(),'departure_at':departure})
        result={'route_count':len(trip['routes']),'recommended':trip['recommended_route_id'],
                'all_complete':all(r['summary']['complete'] for r in trip['routes']),
                'all_blocked':all(r['summary']['blocked'] for r in trip['routes']),
                'all_eligible':all(r['summary']['eligible'] for r in trip['routes'])}
        if variant=='slider':
            forecast=forecast_for_trip(trip['id'],48)
            result.update(arrival_risk=trip['routes'][0]['checkpoints'][0]['risk']['level'],forecast48_risk=forecast['points'][0]['risk']['level'],
                          recommendation_unchanged=get_trip(trip['id'])['result']['recommended_route_id']==trip['recommended_route_id'])
        return result
    if kind == 'api':
        from rest_framework.test import APIClient
        cache.clear()
        client=APIClient()
        variant=spec.get('variant')
        if variant=='seeded':
            # Seed and locate a trip in this CLI process; the web server cache is separate.
            original_set=cache.set
            captured={}
            def remember(key,value,*args,**kwargs):
                if key.startswith('trip:'): captured['id']=key.split(':',1)[1]
                return original_set(key,value,*args,**kwargs)
            with patch.object(cache,'set',side_effect=remember): execute({'kind':'pipeline','variant':'slider'})
            hour=spec.get('hour')
            response=client.get('/api/trips/'+captured['id']+'/forecast/',{} if hour is None else {'hour':hour})
        elif variant=='missing_key':
            with override_settings(TOMTOM_API_KEY=''),patch('routing.serializers.timezone.now',return_value=NOW):
                response=client.post('/api/routes/calculate/',baseline(),format='json')
        elif variant=='bad_json': response=client.post('/api/routes/calculate/',data='{"origin":',content_type='application/json')
        elif variant=='bad_content_type': response=client.post('/api/routes/calculate/',data=json.dumps(baseline()),content_type='text/plain')
        elif variant=='throttle':
            with patch('rest_framework.throttling.AnonRateThrottle.get_rate',return_value='1/hour'),patch('routing.views.search_places',return_value=[]):
                first=client.get('/api/places/',{'q':'Dallas'})
                response=client.get('/api/places/',{'q':'Austin'})
            return {'http_status':response.status_code,'first_status':first.status_code}
        else: response=getattr(client,spec['method'])(spec['path'],spec.get('params',{}),**({'format':'json'} if spec['method']=='post' else {}))
        data=response.json() if 'application/json' in response.get('Content-Type','') else {}
        return {'http_status':response.status_code,'hour':data.get('hour'),'error_code':data.get('error',{}).get('code') if isinstance(data.get('error'),dict) else None}
    raise ValueError('Unknown controlled scenario kind')


def run(case):
    from django.core.cache import cache
    from django.test import override_settings
    cache.clear()
    with override_settings(ALLOWED_HOSTS=['testserver'],SECURE_SSL_REDIRECT=False,DEBUG=False):
        with patch('requests.get',side_effect=RuntimeError('Live HTTP blocked by manual-check utility')):
            try:
                actual=execute(case['_spec'])
                passed=not case['_spec'].get('expect_error') and expected_subset(actual,case['_spec'].get('expect',{}))
            except Exception as error:
                actual={'exception':type(error).__name__,'message':str(error)}
                passed=type(error).__name__==case['_spec'].get('expect_error')
    return {'ID':case['ID'],'result':'PASS' if passed else 'FAIL','sample':case['Sample inputs'],
            'expected':case['_spec'].get('expect',{'exception':case['_spec'].get('expect_error')}),'actual':actual}


def export():
    docs=ROOT/'docs'
    docs.mkdir(exist_ok=True)
    result_path=docs/'MANUAL_TEST_RESULTS.csv'
    old={}
    if result_path.exists():
        with result_path.open(encoding='utf-8-sig',newline='') as handle:
            old={row['ID']:row for row in csv.DictReader(handle)}
    fields=[key for key in CASES[0] if key!='_spec']
    with result_path.open('w',encoding='utf-8-sig',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader()
        for case in CASES:
            row={key:case[key] for key in fields}
            for key in ('Status','Actual result','Notes or evidence'):
                row[key]=old.get(case['ID'],{}).get(key,row[key])
            writer.writerow(row)
    header=MANUAL_HEADER.replace('{TOTAL}',str(len(CASES))).replace('{CONTROLLED}',str(sum(bool(c['_spec']) for c in CASES)))
    lines=[header,'## Requirement coverage\n','| Requirement | Case groups |','|---|---|',
           '| Inputs and human-readable locations | SMK, LOC, VAL, INP |',
           '| Departure, UTC, midnight and DST | TIME, DATE, GEO |',
           '| Up to three distinct real truck routes | SMK, RTE, FLOW |',
           '| Actual road geometry, 10/25/50 miles, final partial interval | SMK, GEO, SUM |',
           '| Arrival-time weather, units and available horizon | WTH, TIME, FLOW |',
           '| Every wind, rain, snow boundary and cargo override | WND, RAN, SNW, LDR, MIX, MIS |',
           '| Distance-weighted miles, Unknown and No Travel exclusion | SUM, RNK, FLOW |',
           '| Exact recommendation priority order and ties | RNK |',
           '| Map, checkpoints, ETAs, summaries, responsive behavior | MAP |',
           '| Real corridor heatmap and 0–48-hour exploration | SLD, FLOW, API |',
           '| Provider errors, timeout, rate limit, cache and recovery | ERR, WTH, API, REC |',
           '| Performance, private configuration and submission | OPS |','']
    for area in dict.fromkeys(case['Area'] for case in CASES):
        group=[case for case in CASES if case['Area']==area]
        lines.extend(['## '+area,'', '| ID | Method | Sample inputs and action | Expected result |','|---|---|---|---|'])
        for case in group:
            clean=lambda value:str(value).replace('|','\\|').replace('\n',' ')
            action=case['Sample inputs']+' — '+case['Steps']
            if case['_spec']: action+=' Command: `python scripts/manual_checks.py --case '+case['ID']+'`.'
            lines.append('| '+' | '.join(map(clean,[case['ID'],case['Method'],action,case['Expected result']]))+' |')
        lines.append('')
    lines.extend([REPORT_TEMPLATE])
    (docs/'MANUAL_TEST_PLAN.md').write_text('\n'.join(lines).rstrip()+'\n',encoding='utf-8')
    print(json.dumps({'total_cases':len(CASES),'controlled_cases':sum(bool(c['_spec']) for c in CASES),
                      'manual_cases':sum(not c['_spec'] for c in CASES),'results_preserved':bool(old),'files':['docs/MANUAL_TEST_PLAN.md','docs/MANUAL_TEST_RESULTS.csv']}))


MANUAL_HEADER = '''# Weather routing manual acceptance tests

This checklist contains **{TOTAL} distinct cases**, including **{CONTROLLED} isolated checks** for exact boundaries and provider failures. Every original assessment requirement maps to a case group. This is requirements coverage, not a claim of measured 100% code coverage or a guarantee that no unlisted defect exists.

## How to work through the cases

1. Start Django on port 8000 and React on port 5173. Keep both terminals running.
2. Start with SMK-01 through SMK-08, then input cases, map/slider cases, and the controlled calculations.
3. Open `docs/MANUAL_TEST_RESULTS.csv` in Excel or another spreadsheet. Change Status to `Pass`, `Fail`, `Blocked`, or `Not applicable`; record actual results and screenshot/error evidence. All cases start as `Not run` for your own testing.
4. Run controlled cases one at a time from the project root with the active virtual environment: `python scripts/manual_checks.py --case WND-03`. You can also use `.\\.venv\\Scripts\\python.exe` instead of `python`.
5. Controlled checks run against application functions or isolated Django handlers with synthetic provider responses. They block live HTTP, do not alter your `.env`, do not restart services, and do not populate the web server's cache. They prove calculation/error paths; they do not replace browser testing of real providers.
6. Share failed case IDs with inputs, expected and actual results, and a screenshot or error. Do not include API keys or `.env` contents.

`python scripts/manual_checks.py --list` lists IDs. `python scripts/manual_checks.py --all-controlled` runs all isolated checks but does not mark your manual results as passed. `python scripts/manual_checks.py --export` regenerates the checklist and preserves existing CSV Status/Actual result/Notes values by ID. Cases without isolated commands must be performed in the browser or host dashboard.

## Baseline inputs and interpretation

- Normal trip: **Dallas, TX → Austin, TX**, **departure one hour from the current time**, **35,000 lb cargo**, **25-mile interval**. Generate a fresh departure instead of copying an old date.
- Unless a row says otherwise, keep this baseline and change only the stated field. Reuse one calculation for map/card/slider inspections to reduce provider calls.
- Boundary weather checks default to cargo **10,000 lb**, with other weather conditions **0**, so cargo overrides cannot accidentally alter the basic wind table.
- Weather values use **wind mph, rain in/hr, snowfall in/hr**. Cargo thresholds are strict `>`; wind bands extend continuously to the next threshold. Rain exactly **1.00** and snow exactly **3.00** stay Severe.
- A recommendation is allowed only when arrival-time weather is complete, there are no No Travel conditions, and truck mode is supported. Different departure times can legitimately change the winner.
- Live routes, mileage, travel times, and weather change. Verify the response and invariants; do not require last run's exact miles, exactly three alternatives, or a particular weather color.
- If every route is unsafe or incomplete, an explicit no-safe-route result is correct. A service, licensing, or quota failure should be recorded with the actual error; do not automatically call it a calculation defect.
- The form rejects past departures; the API deliberately allows up to five minutes of clock skew. Frozen-clock DATE checks use November 6, 2026 at 12:00 UTC without changing the device/server clock. GEO calculations use a synthetic departure at 23:00 UTC to test midnight crossing.
- While inspecting the slider, route lines and recommendations retain **truck-arrival** risk; the corridor layer and second checkpoint-weather section use **departure + selected hours**. Identical real weather across hours is possible; inspect requested timestamps/data rather than requiring a visual color change.
- Preserve secrets and the real key. Use isolated ERR/API cases for missing-key/rate-limit/timeout scenarios. Do not repeatedly flood the live service to trigger throttling; search/calculation requests are limited to 120/hour/process.
- Production checks are **Blocked until deployment**, not Pass. Browser failures remain failures even when an isolated calculation passes.

## Recording results

P0 means essential routing/safety behavior, P1 means normal correctness/usability, and P2 means final operational/submission checks. Priorities and full step descriptions are in the CSV. Do not use `Not applicable` for a required feature merely because it failed; use `Fail` or `Blocked` and explain the cause.

## Findings from preparation

The preparation run executed all 233 isolated checks: **231 passed and 2 failed**. INP-18 accepts JSON boolean `true` as cargo weight instead of rejecting it. DATE-09 raises `ValueError` for an impossible calendar date instead of returning a normal validation error. Keep these as genuine failures to verify, not setup problems. Application behavior is left unchanged while you run the acceptance cases. The CSV still starts as `Not run` for your own results. The 320-pixel layout and keyboard dialog behavior also deserve manual inspection; no pass is claimed for those unexecuted browser cases.
'''

REPORT_TEMPLATE = '''## Result message to share

```text
Case ID: SLD-08
Status: Fail
Origin / destination: Dallas, TX / Austin, TX
Departure and timezone: [actual selected value and device zone]
Cargo / interval: 35000 lb / 25 mi
Steps: [what you clicked, including network throttling if relevant]
Expected: final +48h forecast wins
Actual: [observed behavior]
Browser and screen width: [example: Chrome, 1440 px]
Screenshot or console/API error: [attach or paste sanitized text]
```

For a controlled case, share the printed JSON and ID. For live cases, include the selected timestamp; forecasts and traffic may differ by the time the issue is investigated. Your CSV remains the record of your manual run; isolated utility output does not silently modify it.
'''


def main():
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8',errors='backslashreplace')
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--case',metavar='ID')
    group.add_argument('--list',action='store_true')
    group.add_argument('--all-controlled',action='store_true')
    group.add_argument('--export',action='store_true')
    args=parser.parse_args()
    if len({case['ID'] for case in CASES})!=len(CASES): raise RuntimeError('Duplicate case IDs')
    if args.export: export(); return 0
    if args.list:
        for case in CASES: print(case['ID']+' | '+case['Method']+' | '+case['Sample inputs'])
        return 0
    selected=[case for case in CASES if case['_spec']] if args.all_controlled else [case for case in CASES if case['ID'].upper()==args.case.upper()]
    if not selected: parser.error('Unknown case ID. Use --list.')
    if len(selected)==1 and not selected[0]['_spec']:
        print(json.dumps({key:value for key,value in selected[0].items() if key!='_spec'},indent=2,ensure_ascii=False))
        print('MANUAL: perform these steps and record your result in the CSV. No automatic pass claimed.')
        return 0
    initialize_django()
    import logging
    logging.disable(logging.CRITICAL)
    results=[]
    for case in selected:
        result=run(case)
        results.append(result)
        print(json.dumps(result,ensure_ascii=False,allow_nan=False))
    if args.all_controlled:
        print(json.dumps({'summary':{'executed':len(results),'passed':sum(r['result']=='PASS' for r in results),
                                    'failed':sum(r['result']=='FAIL' for r in results),'manual_results_modified':False}}))
    return 1 if any(result['result']=='FAIL' for result in results) else 0


if __name__=='__main__':
    raise SystemExit(main())
