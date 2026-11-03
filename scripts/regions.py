"""Régions à partir de geoBoundaries.

France : les 13 régions métropolitaines (ADM1).
Angleterre : les 9 régions anglaises, reconstituées en regroupant les unités ADM2,
plus le Pays de Galles (ADM1) pour Cardiff et Swansea.
"""
from pathlib import Path

import geopandas as gpd

GEO = Path(__file__).resolve().parent.parent / "data" / "geo"

REGIONS_ANGLAISES = {
    "Nord-Est": ["County Durham", "Darlington", "Gateshead", "Hartlepool", "Middlesbrough",
                 "Newcastle upon Tyne", "North Tyneside", "Northumberland", "Redcar and Cleveland",
                 "South Tyneside", "Stockton-on-Tees", "Sunderland"],
    "Nord-Ouest": ["Blackburn with Darwen", "Blackpool", "Bolton", "Bury", "Cheshire East",
                   "Cheshire West and Chester", "Cumbria", "Halton", "Knowsley", "Lancashire",
                   "Liverpool", "Manchester", "Oldham", "Rochdale", "Salford", "Sefton", "St. Helens",
                   "Stockport", "Tameside", "Trafford", "Warrington", "Wigan", "Wirral"],
    "Yorkshire": ["Barnsley", "Bradford", "Calderdale", "Doncaster", "East Riding of Yorkshire",
                  "Kingston upon Hull, City of", "Kirklees", "Leeds", "North East Lincolnshire",
                  "North Lincolnshire", "North Yorkshire", "Rotherham", "Sheffield", "Wakefield", "York"],
    "Midlands de l'Est": ["Derby", "Derbyshire", "Leicester", "Leicestershire", "Lincolnshire",
                          "Northamptonshire", "Nottingham", "Nottinghamshire", "Rutland"],
    "Midlands de l'Ouest": ["Birmingham", "Coventry", "Dudley", "Herefordshire, County of", "Sandwell",
                            "Shropshire", "Solihull", "Staffordshire", "Stoke-on-Trent",
                            "Telford and Wrekin", "Walsall", "Warwickshire", "Wolverhampton",
                            "Worcestershire"],
    "Est": ["Bedford", "Cambridgeshire", "Central Bedfordshire", "Essex", "Hertfordshire", "Luton",
            "Norfolk", "Peterborough", "Southend-on-Sea", "Suffolk", "Thurrock"],
    "Londres": ["Barking and Dagenham", "Barnet", "Bexley", "Brent", "Bromley", "Camden",
                "City of London", "Croydon", "Ealing", "Enfield", "Greenwich", "Hackney",
                "Hammersmith and Fulham", "Haringey", "Harrow", "Havering", "Hillingdon", "Hounslow",
                "Islington", "Kensington and Chelsea", "Kingston upon Thames", "Lambeth", "Lewisham",
                "Merton", "Newham", "Redbridge", "Richmond upon Thames", "Southwark", "Sutton",
                "Tower Hamlets", "Waltham Forest", "Wandsworth", "Westminster"],
    "Sud-Est": ["Bracknell Forest", "Brighton and Hove", "Buckinghamshire", "East Sussex", "Hampshire",
                "Isle of Wight", "Kent", "Medway", "Milton Keynes", "Oxfordshire", "Portsmouth",
                "Reading", "Slough", "Southampton", "Surrey", "West Berkshire", "West Sussex",
                "Windsor and Maidenhead", "Wokingham"],
    "Sud-Ouest": ["Bath and North East Somerset", "Bournemouth, Christchurch and Poole",
                  "Bristol, City of", "Cornwall", "Devon", "Dorset", "Gloucestershire",
                  "Isles of Scilly", "North Somerset", "Plymouth", "Somerset", "South Gloucestershire",
                  "Swindon", "Torbay", "Wiltshire"],
}


PAYS = {
    "ALB": "Albanie", "AND": "Andorre", "ARM": "Arménie", "AUT": "Autriche", "AZE": "Azerbaïdjan",
    "BLR": "Biélorussie", "BEL": "Belgique", "BIH": "Bosnie", "BGR": "Bulgarie", "HRV": "Croatie",
    "CYP": "Chypre", "CZE": "Tchéquie", "DNK": "Danemark", "EST": "Estonie", "FRO": "Féroé",
    "FIN": "Finlande", "FRA": "France", "GEO": "Géorgie", "DEU": "Allemagne", "GIB": "Gibraltar",
    "GRC": "Grèce", "HUN": "Hongrie", "ISL": "Islande", "IRL": "Irlande", "ISR": "Israël",
    "ITA": "Italie", "KAZ": "Kazakhstan", "XKX": "Kosovo", "LVA": "Lettonie", "LIE": "Liechtenstein",
    "LTU": "Lituanie", "LUX": "Luxembourg", "MLT": "Malte", "MDA": "Moldavie", "MCO": "Monaco",
    "MNE": "Monténégro", "NLD": "Pays-Bas", "MKD": "Macédoine du Nord", "NOR": "Norvège",
    "POL": "Pologne", "PRT": "Portugal", "ROU": "Roumanie", "RUS": "Russie", "SMR": "Saint-Marin",
    "SRB": "Serbie", "SVK": "Slovaquie", "SVN": "Slovénie", "ESP": "Espagne", "SWE": "Suède",
    "CHE": "Suisse", "TUR": "Turquie", "UKR": "Ukraine",
}
NATIONS_UK = {"England": "Angleterre", "Scotland": "Écosse", "Wales": "Pays de Galles",
              "Northern Ireland": "Irlande du Nord"}
EUROPE_BBOX = (-25, 30, 51, 71.5)  # lon min, lat min, lon max, lat max (Bakou, Kazan à 49-50°E)


def europe():
    morceaux = []
    for iso, nom in PAYS.items():
        g = gpd.read_file(GEO / "europe" / f"{iso}.geojson")
        morceaux.append(g.dissolve().assign(region=nom)[["region", "geometry"]])
    uk = gpd.read_file(GEO / "GBR_ADM1.geojson")
    morceaux.append(uk.assign(region=uk.shapeName.map(NATIONS_UK))[["region", "geometry"]])
    g = gpd.GeoDataFrame(pd_concat(morceaux), crs=4326)
    g["geometry"] = g.geometry.make_valid().clip_by_rect(*EUROPE_BBOX)
    return g[~g.geometry.is_empty].reset_index(drop=True)


ETATS_FR = {
    "California": "Californie", "Pennsylvania": "Pennsylvanie", "Florida": "Floride", "Georgia": "Géorgie",
    "Louisiana": "Louisiane", "North Carolina": "Caroline du Nord", "South Carolina": "Caroline du Sud",
    "Washington": "État de Washington", "New York": "État de New York", "District of Columbia": "Washington D.C.",
    "Ontario": "Ontario", "British Columbia": "Colombie-Britannique", "Quebec": "Québec",
    "New Mexico": "Nouveau-Mexique", "Virginia": "Virginie", "West Virginia": "Virginie-Occidentale",
    "North Dakota": "Dakota du Nord", "South Dakota": "Dakota du Sud", "Tennessee": "Tennessee",
}
NBA_BBOX = (-126, 24, -66, 50.5)


def amerique_du_nord():
    usa = gpd.read_file(GEO / "USA_ADM1.geojson")
    usa = usa[~usa.shapeName.isin(["Alaska", "Hawaii", "Puerto Rico", "Guam", "American Samoa",
                                   "United States Virgin Islands", "Commonwealth of the Northern Mariana Islands"])]
    can = gpd.read_file(GEO / "CAN_ADM1.geojson").to_crs(4326)
    g = gpd.GeoDataFrame(pd_concat([usa[["shapeName", "geometry"]], can[["shapeName", "geometry"]]]), crs=4326)
    g["region"] = g.shapeName.map(lambda n: ETATS_FR.get(n, n))
    g["geometry"] = g.geometry.make_valid().simplify(0.02).clip_by_rect(*NBA_BBOX)
    return g[~g.geometry.is_empty][["region", "geometry"]].reset_index(drop=True)


COMMUNAUTES = {"Andalucía": "Andalousie", "Aragón": "Aragon", "Canarias": "Canaries", "Cantabria": "Cantabrie",
               "Castilla y León": "Castille-et-León", "Castilla-La Mancha": "Castille-La Manche",
               "Cataluña/Catalunya": "Catalogne", "Comunidad Foral de Navarra": "Navarre",
               "Comunidad de Madrid": "Madrid", "Comunitat Valenciana": "Valence", "Extremadura": "Estrémadure",
               "Galicia": "Galice", "Illes Balears": "Baléares", "La Rioja": "La Rioja",
               "País Vasco/Euskadi": "Pays basque", "Principado de Asturias": "Asturies", "Región de Murcia": "Murcie"}
DECALAGE_CANARIES = (5.5, 7.0)  # lon, lat : les Canaries sont rapprochées en encart au sud-ouest


def espagne():
    from shapely.affinity import translate
    g = gpd.read_file(GEO / "ESP_ADM1.geojson")
    g = g[g.shapeName.isin(COMMUNAUTES)].copy()  # sans Ceuta et Melilla
    g["region"] = g.shapeName.map(COMMUNAUTES)
    can = g.region == "Canaries"
    g.loc[can, "geometry"] = g.loc[can, "geometry"].apply(lambda x: translate(x, *DECALAGE_CANARIES))
    return g[["region", "geometry"]].reset_index(drop=True)


def regions(ligue):
    """GeoDataFrame avec une colonne 'region' (une ligne par région jouable)."""
    if ligue == "liga":
        return espagne()
    if ligue == "ligue_des_champions":
        return europe()
    if ligue == "nba":
        return amerique_du_nord()
    if ligue == "france":
        g = gpd.read_file(GEO / "FRA_ADM1.geojson")
        g["region"] = g.shapeName.replace({"Provence-Alpes-Côte d'Azur": "PACA",
                                           "Auvergne-Rhône-Alpes": "Auvergne-Rh.-Alpes",
                                           "Bourgogne-Franche-Comté": "Bourgogne-Fr.-Comté"})
        return g[["region", "geometry"]].reset_index(drop=True)
    adm2 = gpd.read_file(GEO / "GBR_ADM2.geojson")
    nom2reg = {n: r for r, ns in REGIONS_ANGLAISES.items() for n in ns}
    adm2["region"] = adm2.shapeName.map(nom2reg)
    eng = adm2.dropna(subset=["region"]).dissolve("region").reset_index()
    adm1 = gpd.read_file(GEO / "GBR_ADM1.geojson")
    galles = adm1[adm1.shapeName == "Wales"].assign(region="Pays de Galles")
    return gpd.GeoDataFrame(
        pd_concat([eng[["region", "geometry"]], galles[["region", "geometry"]]]), crs=adm2.crs
    ).reset_index(drop=True)


def decor(ligue):
    """Territoires voisins affichés en fond (non jouables) : aucun pour l'instant."""
    return None


def pd_concat(dfs):
    import pandas as pd
    return pd.concat(dfs, ignore_index=True)
