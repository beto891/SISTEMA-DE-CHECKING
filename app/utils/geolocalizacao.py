from geopy.geocoders import Nominatim

def coordenadas_para_endereco(lat, lon):
    geolocator = Nominatim(user_agent="campanha_web")
    location = geolocator.reverse((lat, lon), language="pt")
    if location and location.raw.get("address"):
        address = location.raw["address"]
        bairro = address.get("suburb") or address.get("neighbourhood") or ""
        cidade = address.get("city") or address.get("town") or address.get("village") or ""
        return bairro, cidade
    return "", ""