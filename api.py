import datetime
import re
from urllib.parse import urljoin
import requests


def available_variables(freq, st):
    """
    Returns a list of dictionaries of avaiable variables for the frequency and station type.
    freq is a string and corresponds to the data frequency: hourly, daily or monthly ('h', 'd',
    'm').
    st: type of station, 'automatic', 'conventional'.
    """
    url = "https://apitempo.inmet.gov.br/BNDMET/atributos/"
    st_types = {"automatic": "A301/", "conventional": "83377/"}
    freq_types = ["h", "d", "m"]
    if freq.lower() not in freq_types:
        raise ValueError(f"Invalid frequency. Expected one of: {freq_types}, was given {freq}")
    if st.lower() not in st_types:
        raise ValueError(f"Invalid stton type. Expected one of: {st_types.keys()}")

    url = urljoin(url, st_types[st])
    url = urljoin(url, freq.upper())
    print(f"DEBUG: Making GET request on {url}")
    r = requests.get(url)

    return r.json()


def available_stations(st_type, region=None):
    """
    Returns list of dictionaries, each entry correponding to an avaiable station.
    freq is a string and must be 'h', 'd' or 'm' for hourly, daily and monthly frequencies.
    st_type is a string and must be 'automatic' or 'conventional'.
    region is a string and must be 'N', 'NO', 'S', 'SU' or 'CO' for north, northeast, south,
    southeast and middle west.
    """
    st_types = {"automatic": "/T/R/", "conventional": "/M/R/"}
    regions = ["N", "NO", "S", "SU", "CO"]
    url = "https://apibdmep.inmet.gov.br/"

    if st_type.lower() not in st_types:
        raise ValueError(f"Invalid station type. Expected one of: {st_types}")
    if region.upper() not in regions and region is not None:
        raise ValueError(f"Invalid region. Expected one of: {regions}")

    url = urljoin(url, st_types[st_type])
    if region is None:
        stations = []
        for item in regions:
            print(f"DEBUG: Making GET request on {urljoin(url, item)}")
            r = requests.get(urljoin(url, item))
            stations.extend(r.json())
        return stations
    else:
        print(f"DEBUG: Making GET request on {urljoin(url, region)}")
        r = requests.get(urljoin(url, region))
        return r.json()


def var_codes(freq, st, variables=None):
    """
    Returns variable codes.
    freq: data frequency, 'h', 'd', 'm'.
    st: station type, 'automatic', 'conventonal'.
    When variables param is None returns a list containg all variable codes for a given
    frequency. If variables param is a list, returns a list containing codes for the given
    aliases of descriptions.
    Aliases are only avaiable to automatic station type.
    """
    # {'CODIGO': 'I209',
    # 'TIPO_GERACAO': 'Dado Calculado (Somatório dos valores - Total do Periodo)',
    # 'DESCRICAO': 'PRECIPITACAO TOTAL, MENSAL (AUT)',
    # 'PERIODICIDADE': 'Mensal',
    # 'UNIDADE': 'mm',
    # 'CLASSE': 'Precipitação'}
    freq_types = ["h", "d", "m"]
    st_types = ["automatic", "conventional"]
    if freq.lower() not in freq_types:
        raise ValueError(f"Invalid frequency type. Expected one of: {freq_types}")
    if st.lower() not in st_types:
        raise ValueError(f"Invalid station type. Expected one of: {st_types}")

    if freq.lower() == "h" and st == "automatic":
        variables_aliases = {
            "rain": "I175",
            "P_mean": "I106",
            "P_max": "I615",
            "P_min": "I616",
            "T_mean": "I101",
            "T_max": "I611",
            "T_min": "I612",
            "R_s": "I133",
            "RH_mean": "I105",
            "RH_max": "I617",
            "RH_min": "I618",
            "U_mean": "I111",
            "U_max": "I608",
        }
    elif freq.lower() == "d" and st == "automatic":
        variables_aliases = {
            "rain": "I006",
            "P_mean": "I109",
            "T_mean": "I104",
            "T_max": "I007",
            "T_min": "I008",
            "RH_mean": "I120",
            "RH_min": "I256",
            "U_mean": "I009",
            "U_max": "I621",
        }
    elif freq.lower() == "m" and st == "automatic":
        variables_aliases = {
            "days_raining": "I230",
            "rain": "I209",
            "P_mean": "I219",
            "T_mean": "I220",
            "U_mean": "I218",
            "U_max": "I221",
        }
    else:
        raise Exception("Error. Aliases are only supported with st='automatic'")

    if variables is None:
        codes = [code["CODIGO"] for code in available_variables(freq, st)]
    elif isinstance(variables, list):
        if not all(map(lambda x: isinstance(x, str), variables)):
            raise ValueError("Invalid variables. Expected a str.")
        codes = []
        for var in variables:
            if var in variables_aliases and st == "automatic":
                codes.append(variables_aliases[var])
            elif var in variables_aliases and st == "conventional":
                raise Exception(
                    "Error. Variable aliases currently only work for automatic stations."
                )
            elif re.match(r"I\d{3}", var, flags=re.I):
                # Treat as var code
                codes.append(var)
            else:
                # Treat as description
                for v in available_variables(freq, st):
                    if v["DESCRICAO"] == var:
                        codes.append(v["CODIGO"])
                    else:
                        raise Exception("Invalid description.")
    else:
        raise ValueError("Invalid variables data type. Exepected list or None.")

    return codes


def st_codes(st, region=None, sts=None):
    """
    Returns station codes.
    st: station type, 'automatic', 'conventional'.
    region: nation wide region of the stations, 'N', 'NO', 'S', 'SU' or 'CO'.
    If both region and stations are None, all INMET station codes are returned.

    When stations param is None returns a list contaning all station codes for a given station
    type and region. If stations param is a list, returns a list containing codes for the given
    city state names. Valid stations are a city followed by the state's double char code,
    such as Sorocaba-SP or Coxim/MS or Tres Lagoas MS or Sao Jose do Rio PretoSP. Must be ASCII,
    but case is ignored.
    """
    # {'SG_REGIAO': 'SE', 'CD_OSCAR': '0-2000-0-86827', 'DC_NOME': 'AFONSO CLAUDIO',
    # 'FL_CAPITAL': None, 'DT_FIM_OPERACAO': None, 'CD_SITUACAO': 'Operante',
    # 'TP_ESTACAO': 'Automatica', 'VL_LATITUDE': '-20.10416666',
    # 'CD_WSI': '0-76-0-3200102000000478', 'CD_DISTRITO': ' 06', 'VL_ALTITUDE': '507.48',
    # 'SG_ESTADO': 'ES', 'SG_ENTIDADE': 'INMET', 'CD_ESTACAO': 'A657',
    # 'VL_LONGITUDE': '-41.10694444', 'DT_INICIO_OPERACAO': '2011-09-23T21:00:00.000-03:00'}
    st_types = ["automatic", "conventional"]
    regions = ["N", "NO", "S", "SU", "CO"]
    codes = []

    if st.lower() not in st_types:
        raise ValueError(f"Invalid station type. Expected one of: {st_types}")
    if region.upper() not in regions and region is not None:
        raise ValueError(f"Invalid region. Expected one of: {regions}")
    if not all(map(lambda x: isinstance(x, str), sts)) and sts is not None:
        raise ValueError("Invalid stations. Expected a str.")

    stations_request = available_stations(st, region)
    if sts is None:
        codes = [code["CD_ESTACAO"] for code in stations_request]
    else:
        for station in sts:
            if match := re.match(r"^([ a-z]+)[^a-z]?([A-Z]{2})$", station, flags=re.I):
                codes = [
                    station_["CD_ESTACAO"]
                    for station_ in stations_request
                    if station_["SG_ESTADO"] == match.group(2).upper()
                    and station_["DC_NOME"] == match.group(1).upper()
                ]
            else:
                raise ValueError(
                    "Invalid stations. Expected a string formatted as such: city followed by the "
                    "state double char code (i.e. Sorocaba SP)."
                )

    return codes


def gen_payload(email, freq, st, in_date, fn_date, dec=".", var_sel=None, *st_sel):
    """
    Generates payload dictionary for POST request on the api.

    email: any string.
    freq: 'h', 'd' or 'm'.
    st: 'automatic' or 'conventional'.

    in_date and fn_date: a date formatted as 'YYYY-MM-DD' or 'since' (exclusive for in_date) or a
    datetime object.

    Automatic station type:
    Valid variables (var_sel) for hourly frequency are: 'rain', 'P_mean', 'P_max', 'P_min',
    'T_mean', 'T_max', 'T_min', 'R_s', 'RH_mean', 'RH_max', 'RH_min', 'U_mean', 'U_max',
    any variable description or variable code. For daily frequency: 'rain', 'P_mean', 'T_mean',
    'T_max', 'T_min', 'RH_mean', 'RH_min', 'U_mean', 'U_max', variable description or variable code.
    For monthly frequency, 'days_raining', 'rain', 'P_mean', 'T_mean', 'U_mean', 'U_max',
    descriptions or codes are valid. The resulting data will be aggregated on the specified
    frequency.

    Conventional station type:
    It is necessary to use descriptions for variables.

    Valid st_sel are station codes.
    """
    st_types = {"automatic": "T", "conventional": "M"}
    freq_types = ["h", "d", "m"]
    decimal = {",": "V", ".": "P"}

    if freq.lower() not in freq_types:
        raise ValueError(f"Invalid frequency type. Expected one of: {freq_types}")
    if st.lower() not in st_types:
        raise ValueError(f"Invalid station type. Expected one of: {st_types.keys()}")
    if dec not in decimal:
        raise ValueError(f"Invalid decimal. Expected one of: {decimal.keys()}")

    if isinstance(in_date, datetime.datetime):
        in_date = str(in_date.date())
    elif isinstance(in_date, datetime.date):
        in_date = str(in_date)
    elif isinstance(in_date, str):
        datetime.datetime.strptime(in_date, "%Y-%m-%d")
    else:
        raise ValueError(
            "Invalid initial date type. Expected a datetime object or a %Y-%m-%d formatted string."
        )

    if isinstance(fn_date, datetime.datetime):
        fn_date = str(fn_date.date())
    elif isinstance(fn_date, datetime.date):
        fn_date = str(fn_date)
    elif isinstance(fn_date, str):
        datetime.datetime.strptime(fn_date, "%Y-%m-%d")
    else:
        raise ValueError(
            "Invalid final date type. Expected a datetime object or a %Y-%m-%d formatted string."
        )

    payload = {
        "email": email,
        "tipo_dados": freq.upper(),
        "tipo_estacao": st_types[st],
        "variaveis": var_codes(freq, st, var_sel),
        "estacoes": list(st_sel),
        "data_inicio": in_date,
        "data_fim": fn_date,
        "tipo_pontuacao": decimal[dec],
    }

    return payload


payload = gen_payload(
    "joao.fauvel@unesp.br",
    "h",
    "automatic",
    "2020-12-01",
    datetime.date.today(),
    ".",
    ["rain", "P_mean", "T_mean", "R_s", "RH_mean", "U_mean"],
    "A713",
)

print(payload)
url = "https://apibdmep.inmet.gov.br/requisicao"
response = requests.post(url, data=payload)
print(response.text)

# var = available_variables('m', 'automatic')
# for v in var:
#     print(v)
# sts = stations('automatic', region='SU')
# for st in sts:
#    print(st)
