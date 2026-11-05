def recommend(routes):
    eligible = [route for route in routes if route['summary']['eligible']]
    if not eligible:
        if routes and all(route['summary']['blocked'] for route in routes):
            return None, 'No safe route available. All routes contain No Travel conditions.'
        return None, 'No safe route available. Routes have No Travel conditions, incomplete weather coverage, or unsupported truck sections.'
    def rank(route):
        summary = route['summary']
        return (summary['risk_miles']['Severe'], summary['risk_miles']['High'], summary['average_risk'], route['duration_seconds'], route['id'])
    best = min(eligible, key=rank)
    return best['id'], 'Best eligible route by fewest Severe miles, then High miles, distance-weighted average risk, then travel time.'
