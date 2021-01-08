import datetime
import re
import posixpath
from urllib.parse import urljoin
import requests
from unidecode import unidecode


class BDmep:
    """Python API for querying and requesting data from the BDMEP API from INMET."""

    #: The data frequencies supported by the API: hourly, daily and monthly.
    frequencies = ["h", "d", "m"]
    #: Station types supported by the API: automatic or conventional.
    st_types = ["automatic", "conventional"]
    #: North, northeast, south, southeast, midwest.
    regions = ["n", "no", "s", "su", "co"]
    # API base urls
    #: Base URL for retrieving attribute information.
    base_apitempo = "https://apitempo.inmet.gov.br/BNDMET/atributos/"
    #: Base URL for retrieving station information and for requesting data from the API.
    base_apibdmep = "https://apibdmep.inmet.gov.br/"

    def __init__(self, freq, st="automatic", region=None, attrs=None, sts=None):
        """

        :param freq: String specifying the frequency for querying attribute information and
            requesting data from the API. Can be hourly, daily and monthly ('h', 'd', 'm').
        :param st: String specifying station type for querying attribute information and requesting
            data from the API. Can be 'automatic' or 'conventional'.
        :param region: Either a string or None, in which case all regions are used. It specifies a
            region for querying station information. Can be north, northeast, south, southeast,
            midwest ('n', 'no', 's', 'su', 'co').
        :param attrs: Either a list or None, in which case all attributes are used. The attributes
            must be in code format (i.e. I103), an alias (depends on the frequency and is
            only supported for automatic stations, see below), or by exact description.
            Valid aliases for hourly frequency: 'rain', 'P_mean', 'P_max', 'P_min', 'T_mean',
            'T_max', 'T_min', 'R_s', 'RH_mean', 'RH_max', 'RH_min', 'U_mean', 'U_max'.
            Daily frequency: 'rain', 'P_mean', 'T_mean', 'T_max', 'T_min', 'RH_mean',
            'RH_min', 'U_mean', 'U_max'.
            Monthly frequency: 'days_raining', 'rain', 'P_mean', 'T_mean', 'U_mean', 'U_max'.
        :param sts: Either a list or 'all', in which case all stations are used. It specifies the
            stations in code format (i.e. A713), or in a city state format (i.e. Sorocaba SP,
            Sao José do Rio Preto-SP, CoximMS).
        :raises ValueError: If freq, st or region params are not valid.
        """
        if freq.lower() not in BDmep.frequencies:
            raise ValueError(f"Invalid frequency type. Expected one of: {BDmep.frequencies}")
        if st.lower() not in BDmep.st_types:
            raise ValueError(f"Invalid station type. Expected one of: {BDmep.st_types}")
        if region.lower() not in BDmep.regions and region is not None:
            raise ValueError(f"Invalid region. Expected one of: {BDmep.regions}")

        self.freq = freq
        self.st = st
        self.region = region
        #: List of attribute codes from the attrs param.
        self.attributes = self.__attr_codes(attrs)
        #: Dictionary of aliases.
        self.__aliases = self._attr_aliases() if self.st == "automatic" else None
        #: List of station codes from the sts param.
        self.stations = self.__st_codes(sts)

    def __repr__(self):
        return (
            f"BDmep(freq={self.freq}, st={self.st}, region={self.region}, attrs="
            f"{self.attributes}, sts={self.stations})"
        )

    def _attr_aliases(self):
        """Aliases for common attributes of automatic stations.

        Valid aliases for hourly frequency: 'rain', 'P_mean', 'P_max', 'P_min', 'T_mean',
        'T_max', 'T_min', 'R_s', 'RH_mean', 'RH_max', 'RH_min', 'U_mean', 'U_max'.
        Daily frequency: 'rain', 'P_mean', 'T_mean', 'T_max', 'T_min', 'RH_mean',
        'RH_min', 'U_mean', 'U_max'.
        Monthly frequency: 'days_raining', 'rain', 'P_mean', 'T_mean', 'U_mean', 'U_max'.

        :return: Dictionary of aliases for common attributes.
        :rtype: dict
        """
        if self.freq.lower() == "h" and self.st == "automatic":
            return {
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
        elif self.freq.lower() == "d" and self.st == "automatic":
            return {
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
        elif self.freq.lower() == "m" and self.st == "automatic":
            return {
                "days_raining": "I230",
                "rain": "I209",
                "P_mean": "I219",
                "T_mean": "I220",
                "U_mean": "I218",
                "U_max": "I221",
            }

    def available_attrs(self):
        """Queries the attributes according to frequency and station from the API.

        :return: A list of dictionaries containing the attributes.
        :rtype: list[dict]
        """
        freq_frag = self.freq.upper()
        # TODO: Config file?
        st_frag = "A301".strip("/") if self.st == "automatic" else "83377".strip("/")
        path = posixpath.join(st_frag.strip("/"), freq_frag)
        url = urljoin(BDmep.base_apitempo, path)
        print(f"DEBUG: Making GET request on {url}")
        return requests.get(url).json()

    def available_sts(self):
        """Queries the stations according to station type and region from the API.

        :return: A list of dictionaries containing the stations.
        :rtype: list[dict]
        """
        st_frag = "T/R" if self.st == "automatic" else "M/R"
        if self.region is None:
            sts = []
            for region in BDmep.regions:
                region_frag = region.upper()
                path = posixpath.join(st_frag, region_frag)
                print(f"DEBUG: Making GET request on {urljoin(BDmep.base_apibdmep, path)}")
                sts.extend(requests.get(urljoin(BDmep.base_apibdmep, path)).json())
            return sts
        else:
            region_frag = self.region.upper()
            path = posixpath.join(st_frag, region_frag)
            print(f"DEBUG: Making GET request on {urljoin(BDmep.base_apibdmep, path)}")
            return requests.get(urljoin(BDmep.base_apibdmep, path)).json()

    def __attr_codes(self, attrs_selector):
        """Attribute codes from alias, code (i.e. I109) or exact description. If attrs is None,
        all attribute codes available are returned.

        Valid aliases for hourly frequency: 'rain', 'P_mean', 'P_max', 'P_min', 'T_mean',
        'T_max', 'T_min', 'R_s', 'RH_mean', 'RH_max', 'RH_min', 'U_mean', 'U_max'.
        Daily frequency: 'rain', 'P_mean', 'T_mean', 'T_max', 'T_min', 'RH_mean',
        'RH_min', 'U_mean', 'U_max'.
        Monthly frequency: 'days_raining', 'rain', 'P_mean', 'T_mean', 'U_mean', 'U_max'.

        :param attrs_selector: Either a list or 'all' (to be implemented), in which case all
            attribute codes are returned. Must be in code format (i.e. I103), an alias (depends on
            the frequency and is only supported for automatic stations, see below), or by exact
            description.
        :raises NotImplementedError: If alias is used when self.st == 'conventional'.
        :raises ValueError: If no valid attribute selector is specified.
        :return: A list of strings containing the attribute codes.
        :rtype: list[str]
        """
        if attrs_selector is None:
            return [entry["CODIGO"] for entry in self.available_attrs()]

        codes = []
        for attr in attrs_selector:
            if attr in self.__aliases and self.st == "automatic":
                codes.append(self.__aliases[attr])
            elif attr in self.__aliases and self.st == "conventional":
                raise NotImplementedError(
                    "Attribute aliases currently only work for automatic stations."
                )
            elif re.match(r"I\d{3}", attr, flags=re.I):
                # Treat as attr code
                codes.append(attr.upper())
            else:
                # Treat as description
                for entry in self.available_attrs():
                    if entry["DESCRICAO"] == attr:
                        codes.append(entry["CODIGO"])
                    else:
                        raise Exception("Invalid description.")
        return codes

    def __st_codes(self, sts_selector):
        """Station codes from city state format (i.e. Sorocaba SP) or code (i.e. A713). If
        sts_selector is None, all station codes available for a given region are returned.

        :param sts_selector: Either a list or 'all' (to be implemented), in which case all
            stations are used. It specifies the stations in code format (i.e. A713), or in a city
            state format (i.e. Sorocaba SP, Sao José do Rio Preto-SP, CoximMS).
        :raises ValueError: If no valid station selector is specified.
        :return: A list of strings containing the station codes.
        :rtype: list[str]
        """
        stations = self.available_sts()
        if sts_selector is None:
            return [entry["CD_ESTACAO"] for entry in stations]
        else:
            codes = []
            for selector in sts_selector:
                selector = unidecode(selector)
                if match := re.match(r"^([ a-z]+)[^a-z]?([A-Z]{2})$", selector, flags=re.I):
                    for entry in stations:
                        if (
                            entry["SG_ESTADO"] == match.group(2).upper()
                            and entry["DC_NOME"] == match.group(1).upper()
                        ):
                            codes.append(entry["CD_ESTACAO"])
                elif re.match(r"[A-Z]\d{3}", selector, flags=re.I):
                    codes.append(selector.upper())
                else:
                    raise ValueError(
                        "Invalid stations. Expected a string formatted as such: city followed by "
                        "the state double char code (i.e. Sorocaba SP, Sao José do Rio Preto-SP, "
                        "CoximMS); or a station code (i.e. A713)."
                    )
        return codes


# TODO: Config file?
# TODO: Change station methods behaviour and add 'all' option.
# TODO: Change attribute methods behaviour and add 'all' option.
# TODO: Implement payload preparation and API requesting.
