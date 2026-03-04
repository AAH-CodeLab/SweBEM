// Swedish weather stations grouped by county
// Matched to actual simulation results

export interface WeatherStation {
  id: string;
  name: string;
}

export interface County {
  code: string;
  name: string;
  stations: WeatherStation[];
}

export const CONSTRUCTION_PERIODS = [
  { id: "before-1961", label: "Before 1961" },
  { id: "1961-1975", label: "1961-1975" },
  { id: "1976-1985", label: "1976-1985" },
  { id: "1986-1995", label: "1986-1995" },
  { id: "1996-2005", label: "1996-2005" },
] as const;

export type ConstructionPeriodId = typeof CONSTRUCTION_PERIODS[number]["id"];

export const SCHOOL_HOSPITAL_PERIODS = [
  { id: "before-1961", label: "Before 1961" },
  { id: "1961-1970",   label: "1961-1970" },
  { id: "1971-1980",   label: "1971-1980" },
  { id: "1981-1990",   label: "1981-1990" },
  { id: "1991-2000",   label: "1991-2000" },
  { id: "2000+",       label: "After 2000" },
] as const;
export type SchoolHospitalPeriodId = typeof SCHOOL_HOSPITAL_PERIODS[number]["id"];

// All period ids combined (for components that accept any building type)
export type AnyPeriodId = ConstructionPeriodId | SchoolHospitalPeriodId;

// Helper: get the correct period list for a building type
export function getPeriodsForType(buildingType: string) {
  return (buildingType === "school" || buildingType === "hospital")
    ? SCHOOL_HOSPITAL_PERIODS
    : CONSTRUCTION_PERIODS;
}

// IDF Parameters for each construction period (locked values for display)
export const IDF_PARAMETERS: Record<ConstructionPeriodId, {
  wallUValue: number;
  atticUValue: number;
  groundSlabUValue: number;
  windowUValue: number;
  infiltrationACH: number;
  floorArea: number;
  numberOfFloors: number;
  windowArea: number;
}> = {
  "before-1961": {
    wallUValue: 0.60,
    atticUValue: 0.29,
    groundSlabUValue: 0.28,
    windowUValue: 2.34,
    infiltrationACH: 0.15,
    floorArea: 125,
    numberOfFloors: 2,
    windowArea: 28,
  },
  "1961-1975": {
    wallUValue: 0.31,
    atticUValue: 0.21,
    groundSlabUValue: 0.32,
    windowUValue: 2.30,
    infiltrationACH: 0.15,
    floorArea: 125,
    numberOfFloors: 2,
    windowArea: 28,
  },
  "1976-1985": {
    wallUValue: 0.21,
    atticUValue: 0.15,
    groundSlabUValue: 0.27,
    windowUValue: 2.01,
    infiltrationACH: 0.15,
    floorArea: 125,
    numberOfFloors: 2,
    windowArea: 28,
  },
  "1986-1995": {
    wallUValue: 0.17,
    atticUValue: 0.12,
    groundSlabUValue: 0.24,
    windowUValue: 1.94,
    infiltrationACH: 0.15,
    floorArea: 125,
    numberOfFloors: 2,
    windowArea: 28,
  },
  "1996-2005": {
    wallUValue: 0.20,
    atticUValue: 0.12,
    groundSlabUValue: 0.18,
    windowUValue: 1.87,
    infiltrationACH: 0.08,
    floorArea: 125,
    numberOfFloors: 2,
    windowArea: 28,
  },
};

// MFD (Mid-Rise Apartment) parameters from verified IDFs
// Building: 46.33m x 7.62m, 4 floors (G + Mx2 + T), ~784 m² per floor = ~3135 m² total conditioned area
// ACH: 0.05 for most periods, variable for 1996-2005
export const MFD_IDF_PARAMETERS: Record<ConstructionPeriodId, {
  wallUValue: number;
  atticUValue: number;
  groundSlabUValue: number;
  windowUValue: number;
  infiltrationACH: number;
  floorArea: number;
  numberOfFloors: number;
  windowArea: number;
}> = {
  "before-1961": {
    wallUValue: 0.58,
    atticUValue: 0.36,
    groundSlabUValue: 0.36,
    windowUValue: 2.22,
    infiltrationACH: 0.05,
    floorArea: 3135,
    numberOfFloors: 4,
    windowArea: 133,
  },
  "1961-1975": {
    wallUValue: 0.50,
    atticUValue: 0.28,
    groundSlabUValue: 0.32,
    windowUValue: 2.22,
    infiltrationACH: 0.05,
    floorArea: 3135,
    numberOfFloors: 4,
    windowArea: 133,
  },
  "1976-1985": {
    wallUValue: 0.41,
    atticUValue: 0.20,
    groundSlabUValue: 0.28,
    windowUValue: 2.22,
    infiltrationACH: 0.05,
    floorArea: 3135,
    numberOfFloors: 4,
    windowArea: 133,
  },
  "1986-1995": {
    wallUValue: 0.22,
    atticUValue: 0.15,
    groundSlabUValue: 0.26,
    windowUValue: 1.80,
    infiltrationACH: 0.05,
    floorArea: 3135,
    numberOfFloors: 4,
    windowArea: 133,
  },
  "1996-2005": {
    wallUValue: 0.20,
    atticUValue: 0.13,
    groundSlabUValue: 0.22,
    windowUValue: 1.97,
    infiltrationACH: 0.04,
    floorArea: 3135,
    numberOfFloors: 4,
    windowArea: 133,
  },
};

export const SWEDEN_COUNTIES: County[] = [
  {
    code: "BD",
    name: "Norrbotten",
    stations: [
      { id: "kiruna", name: "Kiruna" },
      { id: "gallivare", name: "Gällivare" },
      { id: "lulea", name: "Luleå" },
      { id: "boden", name: "Boden" },
      { id: "haparanda", name: "Haparanda" },
      { id: "pajala", name: "Pajala" },
      { id: "jokkmokk", name: "Jokkmokk" },
      { id: "arvidsjaur", name: "Arvidsjaur" },
    ],
  },
  {
    code: "AC",
    name: "Västerbotten",
    stations: [
      { id: "umea", name: "Umeå" },
      { id: "skelleftea", name: "Skellefteå" },
      { id: "lycksele", name: "Lycksele" },
      { id: "vilhelmina", name: "Vilhelmina" },
      { id: "storuman", name: "Storuman" },
    ],
  },
  {
    code: "Z",
    name: "Jämtland",
    stations: [
      { id: "ostersund", name: "Östersund" },
      { id: "are", name: "Åre" },
      { id: "sveg", name: "Sveg" },
    ],
  },
  {
    code: "Y",
    name: "Västernorrland",
    stations: [
      { id: "sundsvall", name: "Sundsvall" },
      { id: "harnosand", name: "Härnösand" },
      { id: "ornskoldsvik", name: "Örnsköldsvik" },
    ],
  },
  {
    code: "X",
    name: "Gävleborg",
    stations: [
      { id: "gavle", name: "Gävle" },
      { id: "soderhamn", name: "Söderhamn" },
    ],
  },
  {
    code: "W",
    name: "Dalarna",
    stations: [
      { id: "borlange", name: "Borlänge" },
      { id: "mora", name: "Mora" },
      { id: "malung", name: "Malung" },
      { id: "idre", name: "Idre" },
    ],
  },
  {
    code: "S",
    name: "Värmland",
    stations: [
      { id: "karlstad", name: "Karlstad" },
      { id: "arvika", name: "Arvika" },
      { id: "torsby", name: "Torsby" },
    ],
  },
  {
    code: "T",
    name: "Örebro",
    stations: [
      { id: "orebro", name: "Örebro" },
    ],
  },
  {
    code: "U",
    name: "Västmanland",
    stations: [
      { id: "vasteras", name: "Västerås" },
    ],
  },
  {
    code: "C",
    name: "Uppsala",
    stations: [
      { id: "uppsala", name: "Uppsala" },
    ],
  },
  {
    code: "AB",
    name: "Stockholm",
    stations: [
      { id: "stockholm", name: "Stockholm" },
      { id: "stockholm-arlanda", name: "Stockholm-Arlanda" },
      { id: "stockholm-bromma", name: "Stockholm-Bromma" },
    ],
  },
  {
    code: "D",
    name: "Södermanland",
    stations: [
      { id: "eskilstuna", name: "Eskilstuna" },
      { id: "nykoping", name: "Nyköping" },
    ],
  },
  {
    code: "E",
    name: "Östergötland",
    stations: [
      { id: "norrkoping", name: "Norrköping" },
      { id: "linkoping", name: "Linköping" },
    ],
  },
  {
    code: "F",
    name: "Jönköping",
    stations: [
      { id: "jonkoping", name: "Jönköping" },
    ],
  },
  {
    code: "G",
    name: "Kronoberg",
    stations: [
      { id: "vaxjo", name: "Växjö" },
      { id: "ljungby", name: "Ljungby" },
    ],
  },
  {
    code: "H",
    name: "Kalmar",
    stations: [
      { id: "kalmar", name: "Kalmar" },
    ],
  },
  {
    code: "I",
    name: "Gotland",
    stations: [
      { id: "visby", name: "Visby" },
    ],
  },
  {
    code: "K",
    name: "Blekinge",
    stations: [
      { id: "karlskrona", name: "Karlskrona" },
      { id: "ronneby", name: "Ronneby" },
    ],
  },
  {
    code: "M",
    name: "Skåne",
    stations: [
      { id: "malmo", name: "Malmö" },
      { id: "lund", name: "Lund" },
      { id: "helsingborg", name: "Helsingborg" },
      { id: "kristianstad", name: "Kristianstad" },
      { id: "angelholm", name: "Ängelholm" },
    ],
  },
  {
    code: "N",
    name: "Halland",
    stations: [
      { id: "halmstad", name: "Halmstad" },
    ],
  },
  {
    code: "O",
    name: "Västra Götaland",
    stations: [
      { id: "goteborg", name: "Göteborg" },
      { id: "goteborg-landvetter", name: "Göteborg-Landvetter" },
      { id: "trollhattan", name: "Trollhättan" },
      { id: "skovde", name: "Skövde" },
      { id: "satenas", name: "Såtenäs" },
    ],
  },
];

// Get all station IDs
export function getAllStationIds(): string[] {
  return SWEDEN_COUNTIES.flatMap(county => 
    county.stations.map(station => station.id)
  );
}

// Get station name by ID
export function getStationName(id: string): string {
  for (const county of SWEDEN_COUNTIES) {
    const station = county.stations.find(s => s.id === id);
    if (station) return station.name;
  }
  return id;
}

// Get county name by station ID
export function getCountyByStation(stationId: string): string {
  for (const county of SWEDEN_COUNTIES) {
    if (county.stations.some(s => s.id === stationId)) {
      return county.name;
    }
  }
  return "";
}

// Office IDF parameters - U-values verified from IDF prototype calculations
export const OFFICE_IDF_PARAMETERS:Record<string,{wallUValue:number;atticUValue:number;groundSlabUValue:number;windowUValue:number;infiltrationACH:number;floorArea:number;numberOfFloors:number;windowArea:number;}>={
  'before-1961':{wallUValue:1.096,atticUValue:0.760,groundSlabUValue:0.52,windowUValue:3.14,infiltrationACH:0.15,floorArea:4982,numberOfFloors:3,windowArea:745},
  '1961-1975': {wallUValue:0.930,atticUValue:0.580,groundSlabUValue:0.47,windowUValue:3.14,infiltrationACH:0.15,floorArea:4982,numberOfFloors:3,windowArea:745},
  '1976-1985': {wallUValue:0.298,atticUValue:0.197,groundSlabUValue:0.30,windowUValue:2.00,infiltrationACH:0.15,floorArea:4982,numberOfFloors:3,windowArea:745},
  '1986-1995': {wallUValue:0.298,atticUValue:0.197,groundSlabUValue:0.30,windowUValue:2.00,infiltrationACH:0.15,floorArea:4982,numberOfFloors:3,windowArea:745},
  '1996-2005': {wallUValue:0.232,atticUValue:0.139,groundSlabUValue:0.19,windowUValue:1.50,infiltrationACH:0.11,floorArea:4982,numberOfFloors:3,windowArea:745},
};
// Hotel uses same IDF base as Office
export const HOTEL_IDF_PARAMETERS:Record<string,{wallUValue:number;atticUValue:number;groundSlabUValue:number;windowUValue:number;infiltrationACH:number;floorArea:number;numberOfFloors:number;windowArea:number;}>={
  'before-1961':{wallUValue:1.096,atticUValue:0.760,groundSlabUValue:0.52,windowUValue:3.14,infiltrationACH:0.15,floorArea:11873,numberOfFloors:6,windowArea:1600},
  '1961-1975': {wallUValue:0.930,atticUValue:0.580,groundSlabUValue:0.47,windowUValue:3.14,infiltrationACH:0.15,floorArea:11873,numberOfFloors:6,windowArea:1600},
  '1976-1985': {wallUValue:0.298,atticUValue:0.197,groundSlabUValue:0.30,windowUValue:2.00,infiltrationACH:0.15,floorArea:11873,numberOfFloors:6,windowArea:1600},
  '1986-1995': {wallUValue:0.298,atticUValue:0.197,groundSlabUValue:0.30,windowUValue:2.00,infiltrationACH:0.15,floorArea:11873,numberOfFloors:6,windowArea:1600},
  '1996-2005': {wallUValue:0.232,atticUValue:0.139,groundSlabUValue:0.19,windowUValue:1.50,infiltrationACH:0.11,floorArea:11873,numberOfFloors:6,windowArea:1600},
};
// School IDF parameters - U-values from verified prototype calculations
export const SCHOOL_IDF_PARAMETERS:Record<string,{wallUValue:number;atticUValue:number;groundSlabUValue:number;windowUValue:number;infiltrationACH:number;floorArea:number;numberOfFloors:number;windowArea:number;}>={
  'before-1961':{wallUValue:0.631,atticUValue:0.389,groundSlabUValue:0.52,windowUValue:2.07,infiltrationACH:0.05,floorArea:6871,numberOfFloors:2,windowArea:800},
  '1961-1970': {wallUValue:0.426,atticUValue:0.331,groundSlabUValue:0.47,windowUValue:2.02,infiltrationACH:0.05,floorArea:6871,numberOfFloors:2,windowArea:800},
  '1971-1980': {wallUValue:0.342,atticUValue:0.250,groundSlabUValue:0.30,windowUValue:1.85,infiltrationACH:0.05,floorArea:6871,numberOfFloors:2,windowArea:800},
  '1981-1990': {wallUValue:0.232,atticUValue:0.172,groundSlabUValue:0.30,windowUValue:1.44,infiltrationACH:0.05,floorArea:6871,numberOfFloors:2,windowArea:800},
  '1991-2000': {wallUValue:0.219,atticUValue:0.149,groundSlabUValue:0.19,windowUValue:1.30,infiltrationACH:0.04,floorArea:6871,numberOfFloors:2,windowArea:800},
  '2000+':     {wallUValue:0.208,atticUValue:0.149,groundSlabUValue:0.19,windowUValue:1.20,infiltrationACH:0.03,floorArea:6871,numberOfFloors:2,windowArea:800},
};
// Hospital IDF parameters - U-values from verified prototype calculations
export const HOSPITAL_IDF_PARAMETERS:Record<string,{wallUValue:number;atticUValue:number;groundSlabUValue:number;windowUValue:number;infiltrationACH:number;floorArea:number;numberOfFloors:number;windowArea:number;}>={
  'before-1961':{wallUValue:0.583,atticUValue:0.484,groundSlabUValue:0.52,windowUValue:2.19,infiltrationACH:0.05,floorArea:22422,numberOfFloors:5,windowArea:2400},
  '1961-1970': {wallUValue:0.507,atticUValue:0.371,groundSlabUValue:0.47,windowUValue:1.96,infiltrationACH:0.05,floorArea:22422,numberOfFloors:5,windowArea:2400},
  '1971-1980': {wallUValue:0.393,atticUValue:0.232,groundSlabUValue:0.30,windowUValue:1.66,infiltrationACH:0.05,floorArea:22422,numberOfFloors:5,windowArea:2400},
  '1981-1990': {wallUValue:0.246,atticUValue:0.168,groundSlabUValue:0.30,windowUValue:1.32,infiltrationACH:0.05,floorArea:22422,numberOfFloors:5,windowArea:2400},
  '1991-2000': {wallUValue:0.219,atticUValue:0.149,groundSlabUValue:0.19,windowUValue:1.25,infiltrationACH:0.04,floorArea:22422,numberOfFloors:5,windowArea:2400},
  '2000+':     {wallUValue:0.198,atticUValue:0.168,groundSlabUValue:0.19,windowUValue:1.10,infiltrationACH:0.03,floorArea:22422,numberOfFloors:5,windowArea:2400},
};
export function getIdfParams(bt:string,period:string){const m:Record<string,Record<string,any>>={"single-family-house":IDF_PARAMETERS as any,"mid-rise-apartment":MFD_IDF_PARAMETERS as any,office:OFFICE_IDF_PARAMETERS,hotel:HOTEL_IDF_PARAMETERS,school:SCHOOL_IDF_PARAMETERS,hospital:HOSPITAL_IDF_PARAMETERS};const t=m[bt]??(IDF_PARAMETERS as any);return t[period]??Object.values(t)[0];}
