from dataclasses import dataclass

# from dataclasses import InitVar
import datetime
from enum import Enum
from enum import unique
from collections import namedtuple


@unique
class AttrAliases(Enum):
    I175 = ("rain", "h", "automatic")
    I106 = ("P_mean", "h", "automatic")
    I615 = ("P_max", "h", "automatic")
    I616 = ("P_min", "h", "automatic")
    I101 = ("T_mean", "h", "automatic")
    I611 = ("T_max", "h", "automatic")
    I612 = ("T_min", "h", "automatic")
    I133 = ("R_s", "h", "automatic")
    I105 = ("RH_mean", "h", "automatic")
    I617 = ("RH_max", "h", "automatic")
    I618 = ("RH_min", "h", "automatic")
    I111 = ("U_mean", "h", "automatic")
    I608 = ("U_max", "h", "automatic")
    I006 = ("rain", "d", "automatic")
    I109 = ("P_mean", "d", "automatic")
    I104 = ("T_mean", "d", "automatic")
    I007 = ("T_max", "d", "automatic")
    I008 = ("T_min", "d", "automatic")
    I120 = ("RH_mean", "d", "automatic")
    I256 = ("RH_min", "d", "automatic")
    I009 = ("U_mean", "d", "automatic")
    I621 = ("U_max", "d", "automatic")
    I230 = ("days_raining", "m", "automatic")
    I209 = ("rain", "m", "automatic")
    I219 = ("P_mean", "m", "automatic")
    I220 = ("T_mean", "m", "automatic")
    I218 = ("U_mean", "m", "automatic")
    I221 = ("U_max", "m", "automatic")

    @classmethod
    def unpack(cls) -> namedtuple:
        for code, t in cls.__members__.items():
            alias, freq, st_type = t.value
            A = namedtuple("A", ["code", "alias", "freq", "st_type"])
            yield A(code, alias, freq, st_type)

    @classmethod
    def lookup(
        cls, freq: str = None, st_type: str = None, alias: str = None, code: str = None
    ) -> list[namedtuple]:
        """Lookup enum member by frequency, station type, alias and/or code.

        :rtype: list[namedtuple]
        :return: Returns a filtered list of namedtuples(code, alias, freq, st_type). If all
            parameters are None then a list with all members of the enum is returned.
        """

        res = []
        for member in cls.unpack():
            if freq == member.freq or freq is None:
                if st_type == member.st_type or st_type is None:
                    if alias == member.alias or alias is None:
                        if code == member.code or code is None:
                            res.append(member)

        return res

    @staticmethod
    def lookup_code_by_alias(alias: str, freq: str, st_type: str) -> str or None:
        """Lookup a single code by alias, freq and st_type"""
        try:
            return AttrAliases((alias, freq, st_type)).name
        except ValueError:
            return None

    @staticmethod
    def lookup_alias_by_code(code: str) -> str or None:
        """Lookup a single alias by code."""
        try:
            return AttrAliases[code].name
        except KeyError:
            return None


@dataclass
class Attribute:
    code: str
    freq: str
    unit: str
    desc: str
    class_: str
    alias: str = None

    @staticmethod
    def from_dict(json_dict: dict[str:str]):
        code = json_dict["CODIGO"]
        freq = json_dict["PERIODICIDADE"]
        unit = json_dict["UNIDADE"]
        desc = json_dict["DESCRICAO"]
        class_ = json_dict["CLASSE"]
        alias = AttrAliases.lookup_alias_by_code(code)
        return Attribute(code, freq, unit, desc, class_, alias)


@dataclass
class Station:
    code: str
    city: str
    state: str
    st_type: str
    region: str
    sit: str
    ent: str
    wsi: str
    oscar: str
    lat: float
    lon: float
    alt: float
    dt_oper_in: datetime.datetime
    dt_oper_fn: datetime.datetime = None
    attributes: list[Attribute] = None
    # freq: InitVar[str] = None

    # def __post_init__(self, freq: str):
    #     pass
    #     # if self.attributes is None and freq is not None:
    #     #     self.attributes = BDmep(freq, self.st_type).attributes

    @staticmethod
    def from_dict(
        json_dict: dict[str:str],
        attributes: list[Attribute] = None,
        date_format: str = None,
    ):
        code = json_dict["CD_ESTACAO"]
        city = json_dict["DC_NOME"]
        state = json_dict["SG_ESTADO"]
        st_type = json_dict["TP_ESTACAO"]
        region = json_dict["SG_REGION"]
        sit = json_dict["CD_SITUACAO"]
        ent = json_dict["SG_ENTIDADE"]
        wsi = json_dict["CD_WSI"]
        oscar = json_dict["CD_OSCAR"]
        lat = float(json_dict["VL_LATITUDE"])
        lon = float(json_dict["VL_LONGITUDE"])
        alt = float(json_dict["VL_ALTITUDE"])
        if date_format is None:
            dt_oper_in = datetime.datetime.fromisoformat(json_dict["DT_INICIO_OPERACAO"])
            dt_oper_fn = (
                datetime.datetime.fromisoformat(json_dict["DT_FIM_OPERACAO"])
                if json_dict["DT_FIM_OPERACAO"]
                else None
            )
        else:
            dt_oper_in = datetime.datetime.strptime(json_dict["DT_INICIO_OPERACAO"], date_format)
            dt_oper_fn = (
                datetime.datetime.strptime(json_dict["DT_FIM_OPERACAO"], date_format)
                if json_dict["DT_FIM_OPERACAO"]
                else None
            )

        return Station(
            code,
            city,
            state,
            st_type,
            region,
            sit,
            ent,
            wsi,
            oscar,
            lat,
            lon,
            alt,
            dt_oper_in,
            dt_oper_fn,
            attributes,
        )


# TODO: Take off attributes list of Attribute from station object?
