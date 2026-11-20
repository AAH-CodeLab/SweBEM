"use client";

import { useState, useEffect } from "react";
import { Download, Loader2 } from "lucide-react";
import { StepIndicator } from "@/components/step-indicator";
import { Step1SimulationType } from "@/components/step1-simulation-type";
import type { BatchCounts } from "@/components/step1-simulation-type";
import { Step2BuildingInfo } from "@/components/step2-building-info";
import { Step2BatchBuildingInfo } from "@/components/step2-batch-building-info";
import type { BatchPeriodAllocation } from "@/components/step2-batch-building-info";
import { Step3DesignParameters } from "@/components/step3-design-parameters";
import { Step3CustomParameters } from "@/components/step3-custom-parameters";
import { Step3BatchDesignParameters } from "@/components/step3-batch-design-parameters";
import { Step4Results } from "@/components/step4-results-api";
import { Step4ResultsDisplay } from "@/components/step4-results-display";
import { Step4BatchResults } from "@/components/step4-batch-results";
import { SimulationLoading } from "@/components/simulation-loading";
import { getStationName, getIdfParams, type AnyPeriodId } from "@/lib/sweden-climate-data";

export default function BuildingSimulator() {

  const [currentStep, setCurrentStep] = useState(1);
  const [simulationType, setSimulationType] = useState("pre-configured");
  const [buildingType, setBuildingType] = useState("single-family-house");
  const [weatherStation, setWeatherStation] = useState("lund");
  const [constructionPeriod, setConstructionPeriod] =
    useState<AnyPeriodId>("1986-1995");

  // Custom parameters for real-time simulation
  const [wallU, setWallU] = useState(0.3);
  const [atticU, setAtticU] = useState(0.2);
  const [groundU, setGroundU] = useState(0.2);
  const [ach, setAch] = useState(0.5);
  const [windowType, setWindowType] = useState<"single" | "double" | "triple">("double");
  const [wwr, setWwr] = useState(15);
  const [ventilationType, setVentilationType] = useState<"nv" | "mev-bv" | "mvhr">("mvhr");
  const [heatedFloorArea, setHeatedFloorArea] = useState(125);
  const [numberOfFloors, setNumberOfFloors] = useState(2);

  // Batch simulation state
  const [batchCounts, setBatchCounts] = useState<BatchCounts>({});
  const [batchPeriods, setBatchPeriods] = useState<BatchPeriodAllocation>({});
  const [batchResults, setBatchResults] = useState<any[] | null>(null);
  const [isBatchSimulating, setIsBatchSimulating] = useState(false);
  const [batchError, setBatchError] = useState<string | null>(null);

  // Simulation state for real-time mode
  const [isSimulating, setIsSimulating] = useState(false);
  const [customResult, setCustomResult] = useState<any>(null);
  const [simulationError, setSimulationError] = useState<string | null>(null);

  // Simulation state for pre-configured mode (from API)
  const [preConfigResult, setPreConfigResult] = useState<any>(null);
  const [preConfigHourly, setPreConfigHourly] = useState<any>(null);

  // Update defaults when building type changes
  useEffect(() => {
    const D: Record<string,{a:number;f:number;w:number}> = {
      "single-family-house":{a:125,f:2,w:15},
      "mid-rise-apartment":{a:3135,f:4,w:20},
      "office":{a:4982,f:3,w:30},
      "hotel":{a:11873,f:6,w:30},
      "school":{a:6871,f:2,w:40},
      "hospital":{a:22422,f:5,w:15},
      // Floor area and floors from zone vertex geometry. WWR from fenestration vertex geometry.
      "retail":{a:2294,f:1,w:9},
      "warehouse":{a:4598,f:1,w:3},
    };
    const d=D[buildingType]??D["single-family-house"];
    setHeatedFloorArea(d.a); setNumberOfFloors(d.f); setWwr(d.w);
    if (buildingType==="school"||buildingType==="hospital") setConstructionPeriod("1981-1990");
    if (buildingType==="retail"||buildingType==="warehouse") setConstructionPeriod("2000+");
  }, [buildingType]);

  // Sync custom simulation sliders from IDF values when building type or period changes
  useEffect(() => {
    const params = getIdfParams(buildingType, constructionPeriod);
    if (!params) return;
    setWallU(params.wallUValue);
    setAtticU(params.atticUValue);
    setGroundU(params.groundSlabUValue);
    setAch(params.infiltrationACH);
    const wU = params.windowUValue;
    const diffs: Record<string,number> = { single: Math.abs(wU-2.8), double: Math.abs(wU-2.3), triple: Math.abs(wU-1.8) };
    const best = (Object.entries(diffs).sort((a,b)=>a[1]-b[1])[0][0]) as "single"|"double"|"triple";
    setWindowType(best);
  }, [buildingType, constructionPeriod]);

  const steps = [
    { number: 1, label: "Building Typology" },
    { number: 2, label: "Building Info" },
    { number: 3, label: "Design Parameters" },
    { number: 4, label: "Results" },
  ];

  const isBatch = simulationType === "batch";

  // API call for custom simulation
  const runCustomSimulation = async () => {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    setIsSimulating(true);
    setSimulationError(null);
    setCustomResult(null);
    setCurrentStep(4); // Go to step 4 first to show loading
    
    try {
      const response = await fetch(`${API_BASE}/simulate/custom`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          weatherStation,
          wallU,
          atticU,
          groundU,
          ach,
          windowType,
          wwr,
          ventilationType,
          heatedFloorArea,
          numberOfFloors,
          buildingType,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Simulation failed (${response.status}): ${response.statusText}`);
      }
      
      const result = await response.json();
      setCustomResult(result);
    } catch (error) {
      setSimulationError(error instanceof Error ? error.message : "Simulation failed");
    } finally {
      setIsSimulating(false);
    }
  };

  // API call for batch simulation
  const runBatchSimulation = async () => {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    
    setIsBatchSimulating(true);
    setBatchError(null);
    setBatchResults(null);
    setCurrentStep(4); // Go to step 4 first to show loading

    try {
      // Build list of simulation jobs from batchPeriods
      const jobs: { buildingType: string; periodId: string; count: number }[] = [];
      for (const [btId, periods] of Object.entries(batchPeriods)) {
        for (const [pId, count] of Object.entries(periods)) {
          if (count > 0) jobs.push({ buildingType: btId, periodId: pId, count });
        }
      }

      // Run all simulations in parallel (each unique combo only once)
      const results = await Promise.all(
        jobs.map(async (job) => {
          const response = await fetch(`${API_BASE}/simulate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              weatherStation,
              constructionPeriod: job.periodId,
              buildingType: job.buildingType,
            }),
          });
          if (!response.ok) throw new Error(`Simulation failed for ${job.buildingType} ${job.periodId}`);
          const data = await response.json();
          return {
            buildingType: job.buildingType,
            periodId: job.periodId,
            count: job.count,
            annual: data.annual || data,
            hourly: data.hourly || null,
          };
        })
      );

      setBatchResults(results);
    } catch (error) {
      setBatchError(error instanceof Error ? error.message : "Batch simulation failed");
    } finally {
      setIsBatchSimulating(false);
    }
  };

  const nextStep = async () => {
    if (simulationType === "real-time" && currentStep === 3) {
      await runCustomSimulation();
    } else if (simulationType === "batch" && currentStep === 3) {
      await runBatchSimulation();
    } else if (currentStep < 4) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1);
  };

  // Validation helpers for batch
  const totalBatchCount = Object.values(batchCounts).reduce((a, b) => a + b, 0);
  
  const batchPeriodsValid = () => {
    for (const [btId, count] of Object.entries(batchCounts)) {
      if (count > 0) {
        const periods = batchPeriods[btId] || {};
        const sum = Object.values(periods).reduce((a, b) => a + b, 0);
        if (sum !== count) return false;
      }
    }
    return true;
  };

  const canProceed = () => {
    if (currentStep === 1) {
      if (isBatch) return totalBatchCount >= 2; // Batch requires at least 2 buildings
      return simulationType && buildingType;
    }
    if (currentStep === 2) {
      if (isBatch) return weatherStation && batchPeriodsValid();
      if (simulationType === "real-time") return weatherStation;
      return weatherStation && constructionPeriod;
    }
    return true;
  };

  const downloadResults = () => {
    let result: any = null;
    let hourlyData: any = null;

    if (simulationType === "real-time" && customResult) {
      result = customResult.annual;
      hourlyData = customResult.hourly;
    } else if (simulationType === "pre-configured" && preConfigResult) {
      result = preConfigResult;
      hourlyData = preConfigHourly;
    } else if (simulationType === "batch" && batchResults) {
      // Batch CSV download
      downloadBatchResults();
      return;
    }

    if (!result) return;

    const monthDays = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const monthlyData: { month: string; heating: number; cooling: number }[] = [];
    
    if (hourlyData && hourlyData.heating_power_kw && hourlyData.cooling_power_kw) {
      let hourOffset = 0;
      for (let m = 0; m < 12; m++) {
        const hoursInMonth = monthDays[m] * 24;
        const heatingEnergy = hourlyData.heating_power_kw.slice(hourOffset, hourOffset + hoursInMonth).reduce((a: number, b: number) => a + b, 0);
        const coolingEnergy = hourlyData.cooling_power_kw.slice(hourOffset, hourOffset + hoursInMonth).reduce((a: number, b: number) => a + b, 0);
        monthlyData.push({ month: monthNames[m], heating: Math.round(heatingEnergy), cooling: Math.round(coolingEnergy) });
        hourOffset += hoursInMonth;
      }
    }

    const stationName = getStationName(weatherStation);
    
    let csv = "";
    csv += "Building Energy Simulation Results\n";
    csv += `Generated,${new Date().toISOString()}\n\n`;
    
    csv += "CONFIGURATION\n";
    csv += `Building Type,${buildingType.replace(/-/g, " ")}\n`;
    csv += `Weather Location,${stationName}\n`;
    if (simulationType === "pre-configured") {
      csv += `Construction Period,${constructionPeriod}\n`;
    } else {
      csv += `Simulation Type,Custom Real-Time\n`;
    }
    csv += `Conditioned Floor Area,${result.floor_area} m²\n\n`;
    
    csv += "ANNUAL SUMMARY\n";
    csv += `Total Energy,${Math.round(result.total)},kWh/year\n`;
    csv += `EUI,${result.eui.toFixed(1)},kWh/m²/year\n`;
    csv += `Peak Heating Power,${(result.peak_heating_kw || 0).toFixed(2)},kW\n`;
    csv += `Peak Cooling Power,${(result.peak_cooling_kw || 0).toFixed(2)},kW\n\n`;
    
    csv += "ENERGY BREAKDOWN\n";
    csv += `Heating,${Math.round(result.heating)},kWh/year\n`;
    csv += `Cooling,${Math.round(result.cooling)},kWh/year\n`;
    csv += `DHW,${Math.round(result.dhw)},kWh/year\n`;
    csv += `Lighting,${Math.round(result.lighting)},kWh/year\n`;
    csv += `Equipment,${Math.round(result.equipment)},kWh/year\n\n`;
    
    csv += "MONTHLY ENERGY (kWh)\n";
    csv += "Month,Heating,Cooling\n";
    monthlyData.forEach((m) => {
      csv += `${m.month},${m.heating},${m.cooling}\n`;
    });
    csv += "\n";

    if (hourlyData && hourlyData.heating_power_kw && hourlyData.cooling_power_kw) {
      // Monthly peak power
      csv += "MONTHLY PEAK POWER (kW)\n";
      csv += "Month,Peak Heating (kW),Peak Cooling (kW)\n";
      let hourOffset = 0;
      for (let m = 0; m < 12; m++) {
        const hoursInMonth = monthDays[m] * 24;
        const hSlice = hourlyData.heating_power_kw.slice(hourOffset, hourOffset + hoursInMonth);
        const cSlice = hourlyData.cooling_power_kw.slice(hourOffset, hourOffset + hoursInMonth);
        const peakH = Math.max(...hSlice).toFixed(2);
        const peakC = Math.max(...cSlice).toFixed(2);
        csv += `${monthNames[m]},${peakH},${peakC}\n`;
        hourOffset += hoursInMonth;
      }
      csv += "\n";

      // Full 8760 hourly data
      csv += "HOURLY DATA (8760 hours)\n";
      csv += "Hour,Heating Power (kW),Cooling Power (kW)\n";
      for (let h = 0; h < Math.min(8760, hourlyData.heating_power_kw.length); h++) {
        csv += `${h},${hourlyData.heating_power_kw[h].toFixed(3)},${hourlyData.cooling_power_kw[h].toFixed(3)}\n`;
      }
    }
    
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `energy_results_${weatherStation}_${simulationType === "pre-configured" ? constructionPeriod : "custom"}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const downloadBatchResults = async () => {
    if (!batchResults) return;

    const XLSX = await import("xlsx");
    const stationName = getStationName(weatherStation);
    const monthDays = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    const monthNames = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

    const wb = XLSX.utils.book_new();

    // ── SUMMARY SHEET ──────────────────────────────────────────────
    const summaryRows: any[][] = [
      ["Batch Simulation Results"],
      ["Generated", new Date().toISOString()],
      ["Weather Location", stationName],
      [],
      ["Building Type","Construction Period","Count","Heating (kWh)","Cooling (kWh)","DHW (kWh)","Lighting (kWh)","Equipment (kWh)","Total (kWh)","EUI (kWh/m²)","Floor Area (m²)","Peak Heating (kW)","Peak Cooling (kW)"],
    ];
    let totH=0,totC=0,totDHW=0,totL=0,totE=0,totT=0,totA=0,totPH=0,totPC=0;
    for (const r of batchResults) {
      const a = r.annual || {};
      const h=(a.heating||0)*r.count, c=(a.cooling||0)*r.count, d=(a.dhw||0)*r.count;
      const l=(a.lighting||0)*r.count, e=(a.equipment||0)*r.count, t=(a.total||0)*r.count;
      const area=(a.floor_area||0)*r.count, ph=(a.peak_heating_kw||0)*r.count, pc=(a.peak_cooling_kw||0)*r.count;
      totH+=h;totC+=c;totDHW+=d;totL+=l;totE+=e;totT+=t;totA+=area;totPH+=ph;totPC+=pc;
      summaryRows.push([r.buildingType,r.periodId,r.count,Math.round(h),Math.round(c),Math.round(d),Math.round(l),Math.round(e),Math.round(t),parseFloat((a.eui||0).toFixed(1)),Math.round(area),parseFloat(ph.toFixed(2)),parseFloat(pc.toFixed(2))]);
    }
    summaryRows.push(["TOTAL","",batchResults.reduce((a,r)=>a+r.count,0),Math.round(totH),Math.round(totC),Math.round(totDHW),Math.round(totL),Math.round(totE),Math.round(totT),parseFloat(totA>0?(totT/totA).toFixed(1):"0"),Math.round(totA),parseFloat(totPH.toFixed(2)),parseFloat(totPC.toFixed(2))]);
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(summaryRows), "Summary");

    // ── ONE SHEET PER BUILDING ──────────────────────────────────────
    for (const r of batchResults) {
      const a = r.annual || {};
      const hourlyData = r.hourly || null;

      const rows: any[][] = [
        [`${r.buildingType.replace(/-/g," ")} — ${r.periodId}`],
        [],
        ["CONFIGURATION"],
        ["Building Type", r.buildingType.replace(/-/g," ")],
        ["Construction Period", r.periodId],
        ["Weather Location", stationName],
        ["Count", r.count],
        ["Floor Area (per unit)", `${a.floor_area||0} m²`],
        ["Floor Area (all units)", `${Math.round((a.floor_area||0)*r.count)} m²`],
        [],
        ["ANNUAL SUMMARY (per unit)"],
        ["Total Energy", Math.round(a.total||0), "kWh/year"],
        ["EUI", parseFloat((a.eui||0).toFixed(1)), "kWh/m²/year"],
        ["Peak Heating Power", parseFloat((a.peak_heating_kw||0).toFixed(2)), "kW"],
        ["Peak Cooling Power", parseFloat((a.peak_cooling_kw||0).toFixed(2)), "kW"],
        [],
        ["ANNUAL SUMMARY (all units combined)"],
        ["Total Energy", Math.round((a.total||0)*r.count), "kWh/year"],
        ["Peak Heating Power", parseFloat(((a.peak_heating_kw||0)*r.count).toFixed(2)), "kW"],
        ["Peak Cooling Power", parseFloat(((a.peak_cooling_kw||0)*r.count).toFixed(2)), "kW"],
        [],
        ["ENERGY BREAKDOWN (per unit)"],
        ["Heating", Math.round(a.heating||0), "kWh/year"],
        ["Cooling", Math.round(a.cooling||0), "kWh/year"],
        ["DHW", Math.round(a.dhw||0), "kWh/year"],
        ["Lighting", Math.round(a.lighting||0), "kWh/year"],
        ["Equipment", Math.round(a.equipment||0), "kWh/year"],
      ];

      if (hourlyData?.heating_power_kw?.length > 0) {
        // Monthly
        rows.push([], ["MONTHLY DATA (per unit)"], ["Month","Heating (kWh)","Cooling (kWh)","Peak Heating (kW)","Peak Cooling (kW)"]);
        let hourOffset = 0;
        for (let m = 0; m < 12; m++) {
          const hrs = monthDays[m]*24;
          const hSlice = hourlyData.heating_power_kw.slice(hourOffset, hourOffset+hrs);
          const cSlice = hourlyData.cooling_power_kw.slice(hourOffset, hourOffset+hrs);
          rows.push([monthNames[m], Math.round(hSlice.reduce((a:number,b:number)=>a+b,0)), Math.round(cSlice.reduce((a:number,b:number)=>a+b,0)), parseFloat(Math.max(...hSlice).toFixed(2)), parseFloat(Math.max(...cSlice).toFixed(2))]);
          hourOffset += hrs;
        }
        // Hourly
        rows.push([], ["HOURLY DATA (8760 hours, per unit)"], ["Hour","Heating Power (kW)","Cooling Power (kW)"]);
        for (let h = 0; h < Math.min(8760, hourlyData.heating_power_kw.length); h++) {
          rows.push([h, parseFloat(hourlyData.heating_power_kw[h].toFixed(3)), parseFloat(hourlyData.cooling_power_kw[h].toFixed(3))]);
        }
      }

      const sheetName = `${r.buildingType.replace(/-/g," ").slice(0,20)} ${r.periodId}`.slice(0,31);
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows), sheetName);
    }

    // ── COMBINED NETWORK SHEET ──────────────────────────────────────
    const allHourly = batchResults.filter(r => r.hourly?.heating_power_kw?.length === 8760);
    if (allHourly.length > 0) {
      const netH = new Array(8760).fill(0);
      const netC = new Array(8760).fill(0);
      for (const r of allHourly) {
        for (let h = 0; h < 8760; h++) {
          netH[h] += r.hourly.heating_power_kw[h] * (r.count||1);
          netC[h] += r.hourly.cooling_power_kw[h] * (r.count||1);
        }
      }
      const peakH = parseFloat(Math.max(...netH).toFixed(2));
      const peakC = parseFloat(Math.max(...netC).toFixed(2));

      const netRows: any[][] = [
        ["TOTAL NETWORK — All Buildings Combined"],
        ["Weather Location", stationName],
        [],
        ["Peak Heating (coincident)", peakH, "kW"],
        ["Peak Cooling (coincident)", peakC, "kW"],
        [],
        ["HOURLY DATA - TOTAL NETWORK (8760 hours)"],
        ["Hour","Total Heating (kW)","Total Cooling (kW)"],
      ];
      for (let h = 0; h < 8760; h++) {
        netRows.push([h, parseFloat(netH[h].toFixed(3)), parseFloat(netC[h].toFixed(3))]);
      }
      XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(netRows), "Total Network");
    }

    XLSX.writeFile(wb, `batch_results_${weatherStation}.xlsx`);
  };

  const isAnySimulating = isSimulating || isBatchSimulating;

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="mx-auto max-w-6xl px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          {/* Top bar */}
          <div className="flex items-center justify-start mb-4">
            <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-medium text-orange-600">
              BETA RELEASE
            </span>
          </div>
          
          {/* Title */}
          <div className="text-center">
            <h1 className="text-3xl font-bold tracking-tight text-gray-900 md:text-4xl">
              Building Energy Simulator
            </h1>
            <p className="mt-2 text-lg text-gray-500">For Swedish buildings</p>
          </div>
        </div>

        {/* Step Indicator */}
        <StepIndicator steps={steps} currentStep={currentStep} />

        {/* Error Display */}
        {(simulationError || batchError) && (
          <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600">{simulationError || batchError}</p>
          </div>
        )}

        {/* Content */}
        <div className="mt-8">
          {currentStep === 1 && (
            <Step1SimulationType
              simulationType={simulationType}
              buildingType={buildingType}
              batchCounts={batchCounts}
              onSimulationTypeChange={(newType) => {
                setSimulationType(newType);
                // Clear all results when simulation type changes
                setCustomResult(null);
                setPreConfigResult(null);
                setPreConfigHourly(null);
                setBatchResults(null);
                // Clear batch data when switching away from batch
                if (newType !== "batch") {
                  setBatchCounts({});
                  setBatchPeriods({});
                }
              }}
              onBuildingTypeChange={(newType) => {
                setBuildingType(newType);
                // Clear results when building type changes
                setCustomResult(null);
                setPreConfigResult(null);
                setPreConfigHourly(null);
              }}
              onBatchCountsChange={(newCounts) => {
                setBatchCounts(newCounts);
                // Clear batch results when counts change
                setBatchResults(null);
                // Clear batchPeriods for building types that are now 0
                setBatchPeriods((prev) => {
                  const updated: BatchPeriodAllocation = {};
                  for (const [btId, count] of Object.entries(newCounts)) {
                    if (count > 0 && prev[btId]) {
                      updated[btId] = prev[btId];
                    }
                  }
                  return updated;
                });
              }}
            />
          )}

          {currentStep === 2 && !isBatch && (
            <Step2BuildingInfo
              weatherStation={weatherStation}
              constructionPeriod={constructionPeriod}
              buildingType={buildingType}
              onWeatherStationChange={(newStation) => {
                setWeatherStation(newStation);
                // Clear all results when weather station changes
                setCustomResult(null);
                setPreConfigResult(null);
                setPreConfigHourly(null);
                setBatchResults(null);
              }}
              onConstructionPeriodChange={(newPeriod) => {
                setConstructionPeriod(newPeriod);
                // Clear pre-config results when period changes
                setPreConfigResult(null);
                setPreConfigHourly(null);
              }}
              hideConstructionPeriod={simulationType === "real-time"}
            />
          )}

          {currentStep === 2 && isBatch && (
            <Step2BatchBuildingInfo
              weatherStation={weatherStation}
              onWeatherStationChange={(newStation) => {
                setWeatherStation(newStation);
                // Clear batch results when weather station changes
                setBatchResults(null);
              }}
              batchCounts={batchCounts}
              batchPeriods={batchPeriods}
              onBatchPeriodsChange={(newPeriods) => {
                setBatchPeriods(newPeriods);
                // Clear batch results when periods change
                setBatchResults(null);
              }}
            />
          )}

          {currentStep === 3 && simulationType === "pre-configured" && (
            <Step3DesignParameters constructionPeriod={constructionPeriod} buildingType={buildingType} />
          )}

          {currentStep === 3 && simulationType === "real-time" && (
            <Step3CustomParameters
              wallU={wallU}
              atticU={atticU}
              groundU={groundU}
              ach={ach}
              windowType={windowType}
              wwr={wwr}
              ventilationType={ventilationType}
              heatedFloorArea={heatedFloorArea}
              numberOfFloors={numberOfFloors}
              buildingType={buildingType}
              onWallUChange={setWallU}
              onAtticUChange={setAtticU}
              onGroundUChange={setGroundU}
              onAchChange={setAch}
              onWindowTypeChange={setWindowType}
              onWwrChange={setWwr}
              onVentilationTypeChange={setVentilationType}
              onHeatedFloorAreaChange={setHeatedFloorArea}
              onNumberOfFloorsChange={setNumberOfFloors}
            />
          )}

          {currentStep === 3 && simulationType === "batch" && (
            <Step3BatchDesignParameters batchPeriods={batchPeriods} />
          )}

          {currentStep === 4 && simulationType === "pre-configured" && (
            <Step4Results
              weatherStation={weatherStation}
              constructionPeriod={constructionPeriod}
              buildingType={buildingType}
              onResult={async (annual, hourly) => {
                setPreConfigResult(annual);
                setPreConfigHourly(hourly);
              }}
            />
          )}

          {currentStep === 4 && simulationType === "real-time" && isSimulating && (
            <SimulationLoading buildingType={buildingType} />
          )}

          {currentStep === 4 && simulationType === "real-time" && customResult && !isSimulating && (
            <Step4ResultsDisplay 
              result={customResult.annual}
              hourlyData={customResult.hourly}
              cached={customResult.cached}
              weatherStation={weatherStation}
              customParameters={{ wallU, atticU, groundU, ach, windowType, wwr, ventilationType, heatedFloorArea, numberOfFloors }}
            />
          )}

          {currentStep === 4 && simulationType === "batch" && (
            <Step4BatchResults
              batchPeriods={batchPeriods}
              weatherStation={weatherStation}
              batchResults={batchResults}
              isLoading={isBatchSimulating}
              error={batchError}
            />
          )}
        </div>

        {/* Navigation */}
        <div className="mt-8 flex justify-between">
          <button
            onClick={prevStep}
            disabled={currentStep === 1 || isAnySimulating}
            className="rounded-lg border border-gray-300 bg-white px-6 py-3 font-medium text-gray-700 transition-all hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Back
          </button>
          {currentStep === 4 ? (
            <button
              onClick={downloadResults}
              disabled={isAnySimulating}
              className="flex items-center gap-2 rounded-lg bg-orange-500 px-6 py-3 font-medium text-white transition-all hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              Download Results
            </button>
          ) : (
            <button
              onClick={nextStep}
              disabled={!canProceed() || isAnySimulating}
              className="flex items-center gap-2 rounded-lg bg-orange-500 px-6 py-3 font-medium text-white transition-all hover:bg-orange-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isAnySimulating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Running Simulation...
                </>
              ) : (
                currentStep === 3 && (simulationType === "real-time" || simulationType === "batch")
                  ? "Run Simulation"
                  : "Continue"
              )}
            </button>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-12 border-t border-gray-200 pt-6 text-center">
          <p className="text-sm text-gray-500">
            Developed by Jitendra Pavan Jakkula | MSc, Lund University, Sweden
          </p>
          <p className="text-sm text-gray-500 mt-1">
            Supervised by Akram Abdul Hamid | Assistant Professor, Lund University, Sweden
          </p>
        </footer>
      </div>
    </main>
  );
}
