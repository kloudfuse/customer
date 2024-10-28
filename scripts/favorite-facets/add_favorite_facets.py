import argparse
import requests

# Define the GraphQL API endpoint and headers (update these as needed)
HEADERS = {
    "Content-Type": "application/json",
}

def execute_query(api_url: str, query: str):
    response = requests.post(api_url, json={"query": query}, headers=HEADERS)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Request failed with status code {response.status_code}")
        print("Error:", response.text)
        return None

def get_sources(api_url: str, limit=1000):
    query = f"""
    query {{
      getSources(limit: {limit})
    }}
    """
    data = execute_query(api_url, query)
    return data.get("data", {}).get("getSources", []) if data else []

def get_facet_names(api_url: str, source: str, limit=1000):
    """Fetch facet names for a specific source."""
    query = f"""
    query GetFacetNames {{
      getFacetNames(source: "{source}", limit: {limit}) {{
        facetNames {{
          name
          type
          source
        }}
      }}
    }}
    """
    data = execute_query(api_url, query)
    return data.get("data", {}).get("getFacetNames", {}).get("facetNames", []) if data else []

def add_favorite_facet(api_url: str, source: str, facet: str, facet_group: str, display_name: str, datatype: str):
    """Add a facet as a favorite using the mutation."""
    mutation = f"""
    mutation {{
      addFavoriteFacet(
          source: "{source}",
          facet: "{facet}",
          facetGroup: "{facet_group}",
          displayName: "{display_name}",
          datatype: "{datatype}"
      )
    }}
    """
    data = execute_query(api_url, mutation)
    if data:
        print(f"Successfully added favorite facet '{display_name}' for source '{source}'")
    else:
        print(f"Failed to add favorite facet '{display_name}' for source '{source}'")

def main(api_url: str):
    sources = get_sources(api_url)
    print(sources)
    for source in sources:
        facets = get_facet_names(api_url, source)
        print(facets)
        for facet in facets:
            add_favorite_facet(
                api_url=api_url,
                source=facet["source"],
                facet=facet["name"],
                facet_group=facet["source"],
                display_name=facet["name"],
                datatype=facet["type"]
            )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run GraphQL queries and mutations with a specified API URL.")
    parser.add_argument("api_url", help="The GraphQL API endpoint URL")
    args = parser.parse_args()
    main(args.api_url)

