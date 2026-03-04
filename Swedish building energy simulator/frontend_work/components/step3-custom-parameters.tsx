"use client";

import { useState } from "react";
import { Sliders, Thermometer, Wind, Home, Fan, Layers, Square } from "lucide-react";
import { cn } from "@/lib/utils";

interface Step3CustomProps {
  wallU: number;
  atticU: number;
  groundU: number;
  ach: number;
  windowType: "single" | "double" | "triple";
  wwr: number;
  ventilationType: "self-propelled" | "mechanical-exhaust" | "mechanical-exhaust-hr";
  heatedFloorArea: number;
  numberOfFloors: number;
  buildingType?: string;
  onWallUChange: (value: number) => void;
  onAtticUChange: (value: number) => void;
  onGroundUChange: (value: number) => void;
  onAchChange: (value: number) => void;
  onWindowTypeChange: (value: "single" | "double" | "triple") => void;
  onWwrChange: (value: number) => void;
  onVentilationTypeChange: (value: "self-propelled" | "mechanical-exhaust" | "mechanical-exhaust-hr") => void;
  onHeatedFloorAreaChange: (value: number) => void;
  onNumberOfFloorsChange: (value: number) => void;
}

// Window glazing thresholds for display
const WINDOW_U_RANGES: Record<"single"|"double"|"triple", string> = {
  single: "> 2.5 W/m²K",
  double: "2.1 – 2.5 W/m²K",
  triple: "< 2.1 W/m²K",
};

// Window icon component - Section view showing glass panes
function WindowIcon({ panes, isActive }: { panes: 1 | 2 | 3; isActive: boolean }) {
  const frameColor = isActive ? "#ea580c" : "#9ca3af";
  const glassColor = isActive ? "#f97316" : "#d1d5db";
  const airGapColor = isActive ? "#fed7aa" : "#f3f4f6";
  
  return (
    <svg viewBox="0 0 60 80" className="w-14 h-20">
      {/* Window frame - outer */}
      <rect x="5" y="5" width="50" height="70" rx="2" fill="none" stroke={frameColor} strokeWidth="4" />
      
      {/* Window frame - inner area */}
      <rect x="9" y="9" width="42" height="62" fill={airGapColor} />
      
      {/* Glass panes as vertical lines (section view) */}
      {panes === 1 && (
        <rect x="28" y="12" width="4" height="56" fill={glassColor} rx="1" />
      )}
      
      {panes === 2 && (
        <>
          <rect x="18" y="12" width="4" height="56" fill={glassColor} rx="1" />
          <rect x="38" y="12" width="4" height="56" fill={glassColor} rx="1" />
        </>
      )}
      
      {panes === 3 && (
        <>
          <rect x="13" y="12" width="4" height="56" fill={glassColor} rx="1" />
          <rect x="28" y="12" width="4" height="56" fill={glassColor} rx="1" />
          <rect x="43" y="12" width="4" height="56" fill={glassColor} rx="1" />
        </>
      )}
    </svg>
  );
}

export function Step3CustomParameters({
  wallU,
  atticU,
  groundU,
  ach,
  windowType,
  wwr,
  ventilationType,
  heatedFloorArea,
  numberOfFloors,
  buildingType = "single-family-house",
  onWallUChange,
  onAtticUChange,
  onGroundUChange,
  onAchChange,
  onWindowTypeChange,
  onWwrChange,
  onVentilationTypeChange,
  onHeatedFloorAreaChange,
  onNumberOfFloorsChange,
}: Step3CustomProps) {
  
  const FLOOR_OPTIONS: Record<string, { value: number; label: string }[]> = {
    "single-family-house": [{ value: 1, label: "1 Floor" }, { value: 2, label: "2 Floors" }, { value: 3, label: "3 Floors" }],
    "mid-rise-apartment": [3,4,5].map(n => ({ value: n, label: `${n} Floors` })),
    "office":  [3,4,5,6,7,8,9,10].map(n => ({ value: n, label: `${n} Floors` })),
    "hotel":   [4,5,6,7,8,9,10].map(n => ({ value: n, label: `${n} Floors` })),
    "school":  [{ value: 2, label: "2 Floors (Fixed)" }],
    "hospital":[{ value: 5, label: "5 Floors (Fixed)" }],
  };
  const floorOptions = FLOOR_OPTIONS[buildingType] ?? FLOOR_OPTIONS["single-family-house"];
  const isFixedFloors = buildingType === "school" || buildingType === "hospital";
  const isMFD = buildingType === "mid-rise-apartment";

  const sliderConfig = [
    {
      label: "Wall U-Value",
      value: wallU,
      onChange: onWallUChange,
      unit: "W/m²K",
      min: 0.1,
      max: 2.0,
      step: 0.05,
      icon: Thermometer,
      description: "Lower = better insulation",
    },
    {
      label: "Attic U-Value",
      value: atticU,
      onChange: onAtticUChange,
      unit: "W/m²K",
      min: 0.05,
      max: 1.0,
      step: 0.05,
      icon: Thermometer,
      description: "Lower = better insulation",
    },
    {
      label: "Ground Slab U-Value",
      value: groundU,
      onChange: onGroundUChange,
      unit: "W/m²K",
      min: 0.1,
      max: 0.8,
      step: 0.05,
      icon: Thermometer,
      description: "Lower = better insulation",
    },
    {
      label: "Air Infiltration (ACH)",
      value: ach,
      onChange: onAchChange,
      unit: "h⁻¹",
      min: 0,
      max: 1.0,
      step: 0.01,
      icon: Wind,
      description: "Lower = more airtight",
    },
  ];

  const glazingTypes = [
    { id: "single" as const, label: "Single glazed", panes: 1 as const, rangeLabel: WINDOW_U_RANGES.single },
    { id: "double" as const, label: "Double glazed", panes: 2 as const, rangeLabel: WINDOW_U_RANGES.double },
    { id: "triple" as const, label: "Triple glazed", panes: 3 as const, rangeLabel: WINDOW_U_RANGES.triple },
  ];

  // Calculate dynamic window areas based on building geometry
  // SFH base: 7.8125m x 8m = 62.5 m²/floor, perimeter 31.625m, wall area = 189.75 m² (2fl), base windows ≈ 28 m²
  // MFD base: double-loaded corridor, 8 apartments/floor + corridor, floor area 783.7 m²/floor
  //   IDF exterior wall area = 385.5 m²/floor = 1156.5 m² (3fl), base windows = 230.7 m², base WWR ≈ 20%
  //   Simple perimeter calc doesn't work for MFD (zones have independent exterior walls)
  
  const areaPerFloor = heatedFloorArea / numberOfFloors;
  let totalWallArea: number;
  // IDF-verified base wall areas per floor and base floor areas
  const WALL_BASE: Record<string, { wallPerFloor: number; floorPerFloor: number }> = {
    "single-family-house": { wallPerFloor: 94.875, floorPerFloor: 62.5 },
    "mid-rise-apartment":  { wallPerFloor: 385.5,  floorPerFloor: 783.7 },
    "office":              { wallPerFloor: 329.7,  floorPerFloor: 4982/3 },
    "hotel":               { wallPerFloor: 130.5,  floorPerFloor: 11873/6 },
    "school":              { wallPerFloor: 1492.0, floorPerFloor: 6871/2 },
    "hospital":            { wallPerFloor: 307.4,  floorPerFloor: 22422/5 },
  };
  const base = WALL_BASE[buildingType] ?? WALL_BASE["single-family-house"];
  const linearScale = Math.sqrt(areaPerFloor / base.floorPerFloor);
  totalWallArea = base.wallPerFloor * linearScale * numberOfFloors;

  const wwrOptions = [
    { value: 15, label: "15%", area: `${Math.round(totalWallArea * 0.15)} m²` },
    { value: 20, label: "20%", area: `${Math.round(totalWallArea * 0.20)} m²` },
    { value: 30, label: "30%", area: `${Math.round(totalWallArea * 0.30)} m²` },
    { value: 40, label: "40%", area: `${Math.round(totalWallArea * 0.40)} m²` },
  ];

  const isSchoolOrHospital = buildingType === "school" || buildingType === "hospital";
  const ventilationTypes = [
    { 
      id: "self-propelled" as const, 
      label: "Self-propelled", 
      description: "Natural ventilation only",
      period: isSchoolOrHospital ? "Before 1961" : "Before 1976"
    },
    { 
      id: "mechanical-exhaust" as const, 
      label: "Mechanical Exhaust", 
      description: "Exhaust fan ventilation",
      period: isSchoolOrHospital ? "1961-1980" : "1976-1985"
    },
    { 
      id: "mechanical-exhaust-hr" as const, 
      label: "Mechanical Exhaust + HR", 
      description: "With heat recovery",
      period: isSchoolOrHospital ? "1980+" : "1986+"
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="mb-4 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-100">
            <Sliders className="h-5 w-5 text-orange-500" />
          </div>
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Custom Design Parameters
            </h2>
            <p className="text-sm text-gray-500">
              Adjust parameters to customize your simulation
            </p>
          </div>
        </div>

        {/* Building Summary - Now Dynamic */}
        <div className="grid grid-cols-2 gap-4 rounded-lg bg-gray-50 p-4 md:grid-cols-4">
          <div>
            <p className="text-xs text-gray-500">Building Type</p>
            <p className="font-medium text-gray-900">{
              buildingType === "mid-rise-apartment" ? "Mid-Rise Apartment" :
              buildingType === "office" ? "Office" :
              buildingType === "hotel" ? "Hotel" :
              buildingType === "school" ? "School" :
              buildingType === "hospital" ? "Hospital" :
              "Single Family House"
            }</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Heated Floor Area</p>
            <p className="font-medium text-gray-900">{heatedFloorArea} m²</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Area per Floor</p>
            <p className="font-medium text-gray-900">{areaPerFloor.toFixed(1)} m²</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Number of Floors</p>
            <p className="font-medium text-gray-900">{numberOfFloors}</p>
          </div>
        </div>
      </div>

      {/* Building Geometry Inputs */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Layers className="h-5 w-5 text-orange-500" />
            <h3 className="text-lg font-semibold text-gray-900">
              Building Geometry
            </h3>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Number of Floors - Dropdown */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Number of Heated Floors
              {isFixedFloors && <span className="ml-2 text-xs bg-gray-100 px-1.5 py-0.5 rounded text-gray-500">Fixed</span>}
            </label>
            <select
              value={numberOfFloors}
              disabled={isFixedFloors}
              onChange={(e) => onNumberOfFloorsChange(Number(e.target.value))}
              className="w-full px-4 py-3 rounded-lg border border-gray-300 bg-white text-gray-900 focus:border-orange-500 focus:ring-2 focus:ring-orange-200 transition-all"
            >
              {floorOptions.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </div>

          {/* Heated Floor Area - Input Box */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Total Heated Floor Area (m²)
            </label>
            <div className="relative">
              <input
                type="text"
                inputMode="numeric"
                pattern="[0-9]*"
                value={heatedFloorArea}
                onChange={(e) => {
                  const value = Number(e.target.value);
                  if (!isNaN(value) && value > 0) onHeatedFloorAreaChange(value);
                }}
                className="w-full px-4 py-3 rounded-lg border border-gray-300 bg-white text-gray-900 focus:border-orange-500 focus:ring-2 focus:ring-orange-200 transition-all"
              />
              <span className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400">m²</span>
            </div>
          </div>
        </div>
      </div>

      {/* Window Glazing Type - Clickable */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">
            Window Glazing Type
          </h3>
          <span className="text-sm text-orange-600 font-medium">
            U {WINDOW_U_RANGES[windowType]}
          </span>
        </div>
        
        <div className="grid grid-cols-3 gap-4">
          {glazingTypes.map((type) => {
            const isActive = type.id === windowType;
            return (
              <button
                key={type.id}
                onClick={() => onWindowTypeChange(type.id)}
                className={cn(
                  "flex flex-col items-center p-4 rounded-xl border-2 transition-all cursor-pointer hover:shadow-md",
                  isActive
                    ? "border-orange-500 bg-orange-50"
                    : "border-gray-200 bg-gray-50 hover:border-orange-300"
                )}
              >
                <WindowIcon panes={type.panes} isActive={isActive} />
                <span className={cn(
                  "mt-2 text-sm font-medium",
                  isActive ? "text-orange-600" : "text-gray-600"
                )}>
                  {type.label}
                </span>
                <span className={cn(
                  "text-xs",
                  isActive ? "text-orange-500" : "text-gray-400"
                )}>
                  {type.rangeLabel}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Window-to-Wall Ratio */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Home className="h-5 w-5 text-orange-500" />
            <h3 className="text-lg font-semibold text-gray-900">
              Window-to-Wall Ratio
            </h3>
          </div>
          <span className="text-sm text-orange-600 font-medium">
            {wwr}% ({wwrOptions.find(o => o.value === wwr)?.area})
          </span>
        </div>
        
        <div className="grid grid-cols-4 gap-3">
          {wwrOptions.map((option) => {
            const isActive = option.value === wwr;
            return (
              <button
                key={option.value}
                onClick={() => onWwrChange(option.value)}
                className={cn(
                  "p-3 rounded-lg border-2 transition-all text-center cursor-pointer hover:shadow-md",
                  isActive
                    ? "border-orange-500 bg-orange-50"
                    : "border-gray-200 bg-gray-50 hover:border-orange-300"
                )}
              >
                <span className={cn(
                  "text-lg font-bold block",
                  isActive ? "text-orange-600" : "text-gray-700"
                )}>
                  {option.label}
                </span>
                <span className={cn(
                  "text-xs",
                  isActive ? "text-orange-500" : "text-gray-400"
                )}>
                  {option.area}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Ventilation Type */}
      <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Fan className="h-5 w-5 text-orange-500" />
            <h3 className="text-lg font-semibold text-gray-900">
              Ventilation Type
            </h3>
          </div>
          <span className="text-sm text-orange-600 font-medium">
            {ventilationTypes.find(v => v.id === ventilationType)?.label}
          </span>
        </div>
        
        <div className="grid grid-cols-3 gap-3">
          {ventilationTypes.map((type) => {
            const isActive = type.id === ventilationType;
            return (
              <button
                key={type.id}
                onClick={() => onVentilationTypeChange(type.id)}
                className={cn(
                  "p-4 rounded-lg border-2 transition-all text-left cursor-pointer hover:shadow-md",
                  isActive
                    ? "border-orange-500 bg-orange-50"
                    : "border-gray-200 bg-gray-50 hover:border-orange-300"
                )}
              >
                <span className={cn(
                  "text-sm font-bold block",
                  isActive ? "text-orange-600" : "text-gray-700"
                )}>
                  {type.label}
                </span>
                <span className={cn(
                  "text-xs block mt-1",
                  isActive ? "text-orange-500" : "text-gray-400"
                )}>
                  {type.description}
                </span>
                <span className={cn(
                  "text-xs block mt-1 italic",
                  isActive ? "text-orange-400" : "text-gray-300"
                )}>
                  {type.period}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Interactive Sliders */}
      <div className="space-y-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">
            Building Envelope Parameters
          </h3>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
            Drag sliders to adjust
          </span>
        </div>

        {sliderConfig.map((slider) => {
          const Icon = slider.icon;
          const percent = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;

          return (
            <div key={slider.label} className="space-y-3">
              <div className="flex items-center gap-2">
                <Icon className="h-4 w-4 text-orange-500" />
                <label className="text-sm font-medium text-gray-700">
                  {slider.label}
                </label>
                <span className="ml-auto text-sm font-semibold text-orange-500">
                  {slider.value.toFixed(2)} {slider.unit}
                </span>
              </div>

              {/* Interactive slider */}
              <div className="relative">
                <input
                  type="range"
                  min={slider.min}
                  max={slider.max}
                  step="any"
                  value={slider.value}
                  onChange={(e) => slider.onChange(Math.round(parseFloat(e.target.value) / slider.step) * slider.step)}
                  className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer
                             [&::-webkit-slider-thumb]:appearance-none
                             [&::-webkit-slider-thumb]:w-4
                             [&::-webkit-slider-thumb]:h-4
                             [&::-webkit-slider-thumb]:rounded-full
                             [&::-webkit-slider-thumb]:bg-orange-500
                             [&::-webkit-slider-thumb]:border-2
                             [&::-webkit-slider-thumb]:border-white
                             [&::-webkit-slider-thumb]:shadow
                             [&::-webkit-slider-thumb]:cursor-pointer
                             [&::-moz-range-thumb]:w-4
                             [&::-moz-range-thumb]:h-4
                             [&::-moz-range-thumb]:rounded-full
                             [&::-moz-range-thumb]:bg-orange-500
                             [&::-moz-range-thumb]:border-2
                             [&::-moz-range-thumb]:border-white
                             [&::-moz-range-thumb]:shadow
                             [&::-moz-range-thumb]:cursor-pointer"
                  style={{
                    background: `linear-gradient(to right, #f97316 0%, #f97316 ${percent}%, #e5e7eb ${percent}%, #e5e7eb 100%)`
                  }}
                />
              </div>

              <div className="flex justify-between text-xs text-gray-400">
                <span>
                  {slider.min} {slider.unit}
                </span>
                <span className="text-gray-500">{slider.description}</span>
                <span>
                  {slider.max} {slider.unit}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Info Note */}
      <div className="rounded-lg bg-amber-50 border border-amber-200 p-4">
        <p className="text-sm text-gray-700">
          <strong>Note:</strong> Simulation will run with your custom parameters. 
          This may take 30-60 seconds. Results will be cached for instant retrieval on repeat queries.
        </p>
      </div>
    </div>
  );
}
