#!/usr/bin/env python3
import json

with open('docs/labos-openapi.json', 'r', encoding='utf-8') as f:
    spec = json.load(f)

print('=== OpenAPI Specification Analysis ===')
print(f"Title: {spec.get('info', {}).get('title')}")
print(f"Version: {spec.get('info', {}).get('version')}")
print(f"Total paths: {len(spec.get('paths', {}))}\n")

print('=== All Paths ===')
for p in sorted(spec.get('paths', {}).keys()):
    methods = list(spec['paths'][p].keys())
    print(f'{p}: {methods}')

print('\n=== Security Schemes ===')
security_schemes = spec.get('components', {}).get('securitySchemes', {})
for scheme_name, scheme_details in security_schemes.items():
    print(f'{scheme_name}: {scheme_details.get("type")} ({scheme_details.get("scheme", "N/A")})')

print('\n=== Required Capabilities Mapping ===')
capabilities = {
    '1. report.available webhook / integration event': [
        '/api/v1/integrations/n8n/test',
        '/api/v1/integrations',
        '/api/v1/integrations/logs'
    ],
    '2. report metadata': [
        '/api/v1/reports/{id}/metadata',
        '/api/v1/integrations/reports/{id}/metadata'
    ],
    '3. verified report results': [
        '/api/v1/reports/{id}/results',
        '/api/v1/integrations/reports/{id}/results'
    ],
    '4. patient contact lookup': [
        '/api/v1/patients/lookup'
    ],
    '5. secure patient report access': [
        '/api/v1/reports/{id}/secure-link',
        '/api/v1/public/reports/access/{token}'
    ],
    '6. test catalog': [
        '/api/v1/tests/catalog'
    ],
    '7. branch/location availability': [
        '/api/v1/branches/availability'
    ],
    '8. doctor availability': [
        '/api/v1/doctors/{id}/availability'
    ],
    '9. doctor appointment booking': [
        '/api/v1/bookings/doctor'
    ],
    '10. lab booking': [
        '/api/v1/bookings/lab'
    ],
    '11. customer-care handoff': [
        '/api/v1/customer-care/handoff'
    ]
}

paths = spec.get('paths', {})
all_present = True
for cap, expected_paths in capabilities.items():
    found = [p for p in expected_paths if p in paths]
    status = 'PRESENT' if found else 'MISSING'
    print(f'[{status}] {cap}')
    for p in found:
        print(f'   -> {p}: {list(paths[p].keys())}')
    if not found:
        all_present = False

print(f'\nAll 11 capabilities verified: {all_present}')

# Print detailed schema for each capability
print('\n=== Detailed Endpoint Schemas ===')
for cap, expected_paths in capabilities.items():
    found_paths = [p for p in expected_paths if p in paths]
    if found_paths:
        print(f'\n{cap}')
        for path in found_paths:
            path_spec = spec['paths'][path]
            for method, details in path_spec.items():
                if isinstance(details, dict):
                    print(f'  {method.upper()} {path}')
                    # Print parameters
                    params = details.get('parameters', [])
                    if params:
                        print(f'    Parameters:')
                        for param in params:
                            param_type = param.get('schema', {}).get('type', 'object')
                            required = param.get('required', False)
                            print(f'      - {param.get("name")} ({param.get("in")}): {param_type} [{"required" if required else "optional"}]')
                    # Print request body
                    request_body = details.get('requestBody', {})
                    if request_body:
                        print(f'    Request Body:')
                        content_type = list(request_body.get('content', {}).keys())[0] if request_body.get('content') else 'N/A'
                        print(f'      Content-Type: {content_type}')
                    # Print response schema
                    responses = details.get('responses', {})
                    if responses:
                        print(f'    Responses:')
                        for status_code, response_spec in responses.items():
                            print(f'      {status_code}: {response_spec.get("description", "No description")}')
