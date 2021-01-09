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

    def __init__(self, freq, st_type="automatic", region=None, attrs=None, sts=None):
        """

        :param freq: String specifying the frequency for querying attribute information and
            requesting data from the API. Can be hourly, daily and monthly ('h', 'd', 'm').
        :param st_type: String specifying station type for querying attribute information and
            requesting data from the API. Can be 'automatic' or 'conventional'.
        :param region: Either a string or None, in which case all regions are used. It specifies a
            region for querying station information. Can be north, northeast, south, southeast,
            midwest ('n', 'no', 's', 'su', 'co').
        :param attrs: A list, None or 'all', in which case all attributes are used. The attributes
            must be in code format (i.e. I103), an alias (depends on the frequency and is
            only supported for automatic stations, see below), or by exact description.
            Valid aliases for hourly frequency: 'rain', 'P_mean', 'P_max', 'P_min', 'T_mean',
            'T_max', 'T_min', 'R_s', 'RH_mean', 'RH_max', 'RH_min', 'U_mean', 'U_max'.
            Daily frequency: 'rain', 'P_mean', 'T_mean', 'T_max', 'T_min', 'RH_mean',
            'RH_min', 'U_mean', 'U_max'.
            Monthly frequency: 'days_raining', 'rain', 'P_mean', 'T_mean', 'U_mean', 'U_max'.
        :param sts: A list, None or 'all', in which case all stations are used. It specifies the
            stations in code format (i.e. A713), or in a city state format (i.e. Sorocaba SP,
            Sao José do Rio Preto-SP, CoximMS).
        :raises ValueError: If freq, st_type or region params are not valid.
        """
        if sts is None:
            sts = []
        if attrs is None:
            attrs = []
        if freq.lower() not in BDmep.frequencies:
            raise ValueError(f"Invalid frequency type. Expected one of: {BDmep.frequencies}")
        if st_type.lower() not in BDmep.st_types:
            raise ValueError(f"Invalid station type. Expected one of: {BDmep.st_types}")
        if region is not None and region.lower() not in BDmep.regions:
            raise ValueError(f"Invalid region. Expected one of: {BDmep.regions}")

        self.freq = freq
        self.st_type = st_type
        self.region = region
        #: Dictionary of aliases.
        self._aliases = self._attr_aliases() if self.st_type == "automatic" else None
        #: Raw response from the API.
        self.attr_response = self.query_attrs()
        self.st_response = self.query_sts()
        #: List of attribute codes from the attrs param.
        self.attributes = self.__attr_codes(attrs)
        #: List of station codes from the sts param.
        self.stations = self.__st_codes(sts)

    def __repr__(self):
        return (
            f"BDmep(freq={self.freq}, st_type={self.st_type}, region={self.region}, attrs="
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
        if self.freq.lower() == "h" and self.st_type == "automatic":
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
        elif self.freq.lower() == "d" and self.st_type == "automatic":
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
        elif self.freq.lower() == "m" and self.st_type == "automatic":
            return {
                "days_raining": "I230",
                "rain": "I209",
                "P_mean": "I219",
                "T_mean": "I220",
                "U_mean": "I218",
                "U_max": "I221",
            }

    def query_attrs(self):
        """Queries the attributes according to frequency and station from the API.

        :return: A list of dictionaries containing the attributes.
        :rtype: list[dict]
        """
        freq_frag = self.freq.upper()
        # TODO: Config file?
        st_frag = "A301" if self.st_type == "automatic" else "83377"
        path = posixpath.join(st_frag.strip("/"), freq_frag)
        url = urljoin(BDmep.base_apitempo, path)
        print(f"DEBUG: GET request: {url}")
        return requests.get(url).json()

    def query_sts(self):
        """Queries the stations according to station type and region from the API.

        :return: A list of dictionaries containing the stations.
        :rtype: list[dict]
        """
        st_frag = "T/R" if self.st_type == "automatic" else "M/R"
        if self.region is None:
            response = []
            for region in BDmep.regions:
                region_frag = region.upper()
                path = posixpath.join(st_frag, region_frag)
                print(f"DEBUG: GET request: {urljoin(BDmep.base_apibdmep, path)}")
                response.extend(requests.get(urljoin(BDmep.base_apibdmep, path)).json())
            return response
        else:
            region_frag = self.region.upper()
            path = posixpath.join(st_frag, region_frag)
            print(f"DEBUG: GET request: {urljoin(BDmep.base_apibdmep, path)}")
            return requests.get(urljoin(BDmep.base_apibdmep, path)).json()

    def __attr_codes(self, attrs_selector):
        """Attribute codes from alias, code (i.e. I109) or exact description. If attrs is 'all',
        all attribute codes available are returned.

        Valid aliases for hourly frequency: 'rain', 'P_mean', 'P_max', 'P_min', 'T_mean',
        'T_max', 'T_min', 'R_s', 'RH_mean', 'RH_max', 'RH_min', 'U_mean', 'U_max'.
        Daily frequency: 'rain', 'P_mean', 'T_mean', 'T_max', 'T_min', 'RH_mean',
        'RH_min', 'U_mean', 'U_max'.
        Monthly frequency: 'days_raining', 'rain', 'P_mean', 'T_mean', 'U_mean', 'U_max'.

        :param attrs_selector: Either a list or 'all', in which case all attribute codes are
            returned. Must be in code format (i.e. I103), an alias (depends on the frequency and
            is only supported for automatic stations, see above), or by exact description. When
            given an empty list an empty list is returned.
        :raises ValueError: If no valid attribute selector is is given: it is either None or it
            doesn't match any actual attribute from the API.
        :return: A list of strings containing the attribute codes or an empty list.
        :rtype: list[str]
        """
        if not attrs_selector:
            return []
        elif attrs_selector == "all":
            return [entry["CODIGO"] for entry in self.attr_response]

        codes = []
        for selector in attrs_selector:
            if selector in self._aliases:
                codes.append(self._aliases[selector])
            elif re.match(r"I\d{3}", selector, flags=re.I):
                try:
                    next(
                        codes.append(entry["CODIGO"])
                        for entry in self.attr_response
                        if entry["CODIGO"] == selector.upper()
                    )
                except StopIteration as e:
                    raise ValueError(
                        f"Parameter '{selector}' given doesn't correspond to any attribute."
                    ) from e
            else:
                # Treat as description
                try:
                    next(
                        codes.append(entry["CODIGO"])
                        for entry in self.attr_response
                        if entry["DESCRICAO"].lower() == selector.lower()
                    )
                except StopIteration as e:
                    raise ValueError(
                        f"Parameter '{selector}' given doesn't correspond to any attribute."
                    ) from e
        return codes

    def __st_codes(self, sts_selector):
        """Station codes from city state format (i.e. Sorocaba SP) or code (i.e. A713). If
        sts_selector is 'all', all station codes available for a given region are returned.

        :param sts_selector: Either a list or 'all', in which case all stations are used. It
            specifies the stations in code format (i.e. A713), or in a city state format (i.e.
            Sorocaba SP, Sao José do Rio Preto-SP, CoximMS). When given an empty list, an empty
            list is returned.
        :raises ValueError: If no valid station selector is given: it is either None or it
            doesn't match any actual station from the API.
        :return: A list of strings containing the station codes.
        :rtype: list[str]
        """

        if not sts_selector:
            return []
        elif sts_selector == "all":
            return [entry["CD_ESTACAO"] for entry in self.st_response]

        codes = []
        for selector in sts_selector:
            selector = unidecode(selector)
            if match := re.match(r"^([ a-z]+)[^a-z]?([A-Z]{2})$", selector, flags=re.I):
                try:
                    next(
                        codes.append(entry["CD_ESTACAO"])
                        for entry in self.st_response
                        if entry["SG_ESTADO"] == match.group(2).upper().strip()
                        and entry["DC_NOME"] == match.group(1).upper().strip()
                    )
                except StopIteration as e:
                    raise ValueError(
                        f"Parameter '{selector}' given doesn't correspond to any station."
                    ) from e
            elif re.match(r"[A-Z]\d{3}", selector, flags=re.I):
                try:
                    next(
                        codes.append(entry["CD_ESTACAO"])
                        for entry in self.st_response
                        if entry["CD_ESTACAO"] == selector.upper()
                    )
                except StopIteration as e:
                    raise ValueError(
                        f"Parameter '{selector}' given doesn't correspond to any station."
                    ) from e
            else:
                raise ValueError(
                    "Invalid stations. Expected a string formatted as such: city followed by "
                    "the state double char code (i.e. Sorocaba SP, Sao José do Rio Preto-SP, "
                    "CoximMS); or a station code (i.e. A713)."
                )
        return codes

    # def set_attr(self, attrs_selector):
    #     self.attributes = self.__attr_codes(attrs_selector)


def st_codes(st_type="automatic", region=None, st="all"):
    """Station codes from parameters."""
    api = BDmep(freq="h", st_type=st_type, region=region, attrs=None, sts=st)
    return api.stations


def attr_codes(freq, st_type="automatic", attr="all"):
    """Attribute codes from parameters."""
    api = BDmep(freq=freq, st_type=st_type, region=None, attrs=attr, sts=None)
    return api.attributes


# TODO: Change BDmep.attributes() and BDmep.__st_codes() to return a dict {name: code}
# TODO: Add instance attributes for json response.
# TODO: Rename class parameters to match st_codes() and attr_codes()
# TODO: Config file?
# TODO: Implement payload preparation and API requesting.
