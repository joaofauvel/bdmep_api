from modals import Station, Attribute, AttrAliases
from unidecode import unidecode
import requests
from urllib.parse import urljoin
import posixpath
import re


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

    def __init__(self, freq: str, st_type: str, region: str = None):
        if freq.lower() not in BDmep.frequencies:
            raise ValueError(f"Invalid frequency type. Expected one of: {BDmep.frequencies}")
        if st_type.lower() not in BDmep.st_types:
            raise ValueError(f"Invalid station type. Expected one of: {BDmep.st_types}")
        if region is not None and region.lower() not in BDmep.regions:
            raise ValueError(f"Invalid region. Expected one of: {BDmep.regions}")
        self.freq = freq
        self.st_type = st_type
        self.region = region

    @property
    def attributes(self) -> list[Attribute]:
        """Queries the attributes according to frequency and station from the API.

        :return: A list of bdmep.modals.Attribute objects representing the attributes.
        :rtype: list[Attribute]
        """

        freq_frag = self.freq.upper()
        st_frag = "A301" if self.st_type == "automatic" else "83377"
        path = posixpath.join(st_frag, freq_frag)
        url = urljoin(BDmep.base_apitempo, path)
        print(f"DEBUG: GET request: {url}")
        r = requests.get(url)
        r.raise_for_status()
        return [Attribute.from_dict(attribute) for attribute in r.json()]

    @property
    def stations(self) -> list[Station]:
        """Queries the stations according to station type and region from the API.

        :return: A list of bdmep.modals.Station objects representing the stations.
        :rtype: list[Station]
        """

        st_frag = "T/R" if self.st_type == "automatic" else "M/R"
        if self.region is None:
            stations = []
            for region in BDmep.regions:
                region_frag = region.upper()
                path = posixpath.join(st_frag, region_frag)
                url = urljoin(BDmep.base_apibdmep, path)
                print(f"DEBUG: GET request: {url}")
                r = requests.get(url)
                r.raise_for_status()
                stations.extend([Station.from_dict(entry) for entry in r.json()])
            return stations

        region_frag = self.region.upper()
        path = posixpath.join(st_frag, region_frag)
        url = urljoin(BDmep.base_apibdmep, path)
        print(f"DEBUG: GET request: {url}")
        r = requests.get(url)
        return [Station.from_dict(entry) for entry in r.json()]

    def _attributes_has_code(self, code: str) -> bool:
        if code in [attr.code for attr in self.attributes]:
            return True
        else:
            return False

    def _stations_has_code(self, code: str) -> bool:
        if code in [st.code for st in self.stations]:
            return True
        else:
            return False

    def _parse_attrs(self, attr_selector: list[str]) -> list[str]:
        if attr_selector == "all":
            return [attr.code for attr in self.attributes]

        attributes = []
        for sel in attr_selector:
            # If an attribute code is given
            if re.match(r"I\d{3}", sel, flags=re.I) and self._attributes_has_code(code=sel):
                attributes.append(sel)
            # If an attribute alias is given
            elif code := AttrAliases.lookup_code_by_alias(sel, self.freq, self.st_type):
                attributes.append(code)
            else:
                raise ValueError(
                    f"Parameter attr_selector given doesn't correspond to any attribute."
                )
        return attributes
        # TODO: Match other parameters.
        # TODO: Check if it is an alias first.

    def _parse_sts(self, st_selector: list[str]) -> list[str]:
        if st_selector == "all":
            return [st.code for st in self.stations]

        stations = []
        for sel in st_selector:
            sel = unidecode(sel)
            # If a station code is given
            if re.match(r"[A-Z]\d{3}", sel, flags=re.I) and self._stations_has_code(code=sel):
                stations.append(sel)
            # If a station city-state is given
            elif match := re.match(r"^([ a-z]+)[^a-z]?([A-Z]{2})$", sel, flags=re.I):
                stations.append(
                    [
                        st.code
                        for st in self.stations
                        if st.state == match.group(2).upper().strip()
                        and st.city == match.group(1).upper().strip()
                    ]
                )
            else:
                raise ValueError(f"Parameter st_selector given doesn't correspond to any station.")

        # TODO: Match other parameters.
        # TODO: Check if it is an alias first.

    def prepare_payload(
        self, email: str, st_selector: list = "all", attr_selector: list = "all", dec: str = "."
    ) -> dict[str]:
        st_types = {"automatic": "T", "conventional": "M"}
        #: Decimal separator for preparing payload
        decimal = {".": "P", ",": "V"}
        attributes = self._parse_attrs(attr_selector)
        stations = self._parse_sts(st_selector)

        payload = {
            "email": email,
            "tipo_dados": self.freq.upper(),
            "tipo_estacao": st_types[self.st_type],
            "variaveis": attributes,
            "estacoes": stations,
            "data_inicio": "",
            "data_fim": "",
            "tipo_pontuacao": decimal[dec],
        }
        return payload

        # TODO: Dates


# TODO: Create a unified _parse method?
# TODO: has_station method. Similar to AttrAliases.lookup()
# TODO: Ability to not specify station type?
# TODO: Work on the docstrings and tests
# TODO: namedtuple URL fragments as a class attribute
