"""Part 1: Rebuild Material_Master with 26 groups, 252 material codes."""
import sqlite3, os, shutil

SRC = "/sessions/vibrant-zealous-mccarthy/s2c_sourcesense.db"
conn = sqlite3.connect(SRC)
conn.execute("PRAGMA foreign_keys = OFF")
c = conn.cursor()

# Clear material-dependent tables first (FK order)
for t in ["Procurement_Historical_Pricing","Vendor_History","RFQ_Submissions",
          "Consolidated_PRs","Master_PR_Data","Material_References","Material_Master"]:
    c.execute(f"DELETE FROM {t}")

# ── 26 material groups ──────────────────────────────────────────────────────
# fmt: (Material_Code, Material_Number, Description, Group, Group_Desc, HSN,
#        Base_UOM, Category, LPP, LPP_Currency, LPP_Date, LPP_Vendor,
#        Lead_Days, MOQ, Safety_Stock, Reorder, ABC, Criticality,
#        MSDS, Spec_Doc, Created_At, Updated_At)

NOW = "2025-11-01 09:00:00"
UP  = "2025-11-01 09:00:00"

materials = []

def m(code, num, desc, grp, grp_desc, hsn, uom, cat, lpp, lpp_v,
      lead, moq, ss, rop, abc, crit, msds=0, spec=None):
    materials.append((
        code, num, desc, grp, grp_desc, hsn, uom, cat,
        lpp, "INR", "2025-10-01", lpp_v,
        lead, moq, ss, rop, abc, crit, msds, spec, NOW, UP
    ))

# ── MRO-BRG  Bearings & Bushings (10) ───────────────────────────────────────
m("1000-10042678","10042678","Deep Groove Ball Bearing 6205-2RS","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",462,"V-20045",21,50,100,200,"A","Critical")
m("1000-10042679","10042679","Spherical Roller Bearing 22210 EK","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",2850,"V-20045",28,20,40,80,"A","Critical")
m("1000-10042680","10042680","Tapered Roller Bearing 30206","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",780,"V-20046",21,30,60,120,"B","High")
m("1000-10042681","10042681","Needle Roller Bearing HK2020","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",320,"V-20047",14,100,200,400,"C","Low")
m("1000-10042682","10042682","Angular Contact Bearing 7205B","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",1240,"V-20045",21,20,40,80,"B","High")
m("1000-10042683","10042683","Thrust Ball Bearing 51205","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",680,"V-20046",21,40,80,160,"C","Medium")
m("1000-10042684","10042684","Cylindrical Roller Bearing NJ205","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",1480,"V-20045",28,20,40,80,"B","High")
m("1000-10042685","10042685","Pillow Block Bearing UCF205","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",1650,"V-20054",14,15,30,60,"C","Medium")
m("1000-10042686","10042686","Bronze Bush 50x60x40mm","MRO-BRG","Bearings & Bushings","83072000","NO","Supply",540,"V-20054",10,20,50,100,"C","Low")
m("1000-10042687","10042687","Self-Aligning Ball Bearing 1205 ETN9","MRO-BRG","Bearings & Bushings","84829100","NO","Supply",890,"V-20046",21,30,60,120,"B","Medium")

# ── MRO-ELE  Electrical Components (10) ─────────────────────────────────────
m("1000-10055001","10055001","Contactor 3-Pole 25A 240V AC","MRO-ELE","Electrical Components","85389000","NO","Supply",1450,"V-20048",14,10,20,40,"B","High")
m("1000-10055002","10055002","Thermal Overload Relay 16-25A","MRO-ELE","Electrical Components","85363000","NO","Supply",890,"V-20048",14,15,30,60,"B","Medium")
m("1000-10055003","10055003","VFD Drive 7.5kW 3-Phase 415V","MRO-ELE","Electrical Components","85044000","NO","Supply",28500,"V-20049",42,2,4,6,"A","Critical",0,"DOC-SPEC-003")
m("1000-10055004","10055004","MCB 3-Pole 32A C-Curve","MRO-ELE","Electrical Components","85362000","NO","Supply",560,"V-20048",10,20,40,80,"C","Medium")
m("1000-10055005","10055005","MCCB 3-Pole 100A Fixed","MRO-ELE","Electrical Components","85362000","NO","Supply",4200,"V-20048",21,5,10,20,"B","High")
m("1000-10055006","10055006","Push Button Station Double — Start/Stop","MRO-ELE","Electrical Components","85365000","NO","Supply",980,"V-20049",10,10,20,40,"C","Low")
m("1000-10055007","10055007","Limit Switch XCMD2102L1","MRO-ELE","Electrical Components","85363000","NO","Supply",2100,"V-20048",14,8,16,32,"B","High")
m("1000-10055008","10055008","Terminal Block 4mm2 Grey","MRO-ELE","Electrical Components","85369090","NO","Supply",38,"V-20049",7,200,400,800,"C","Low")
m("1000-10055009","10055009","Proximity Sensor M18 10-30V DC NPN","MRO-ELE","Electrical Components","85044000","NO","Supply",1850,"V-20049",14,10,20,40,"B","Medium")
m("1000-10055010","10055010","Phase Failure Relay 3-Phase 415V","MRO-ELE","Electrical Components","85363000","NO","Supply",3200,"V-20048",21,5,10,20,"B","High")

# ── MRO-HYD  Hydraulics (10) ────────────────────────────────────────────────
m("1000-10067001","10067001","Hydraulic Cylinder 80mm Bore 500mm Stroke","MRO-HYD","Hydraulics","84122100","NO","Supply",18500,"V-20050",35,3,6,10,"A","Critical",0,"DOC-SPEC-004")
m("1000-10067002","10067002","Hydraulic Hose 1/2in 4000PSI 2M","MRO-HYD","Hydraulics","40094200","M","Supply",650,"V-20050",7,50,100,200,"C","Medium")
m("1000-10067003","10067003","Directional Control Valve 4/3 Way","MRO-HYD","Hydraulics","84812090","NO","Supply",12800,"V-20050",28,2,4,6,"A","High",0,"DOC-SPEC-005")
m("1000-10067004","10067004","Hydraulic Filter Element 10 Micron","MRO-HYD","Hydraulics","84219900","NO","Supply",1200,"V-20058",14,10,20,40,"B","High")
m("1000-10067005","10067005","Hydraulic Pump Gear Type 16cc/rev","MRO-HYD","Hydraulics","84136010","NO","Supply",22000,"V-20050",42,2,4,6,"A","Critical")
m("1000-10067006","10067006","Pressure Relief Valve 350 Bar 3/4in BSP","MRO-HYD","Hydraulics","84812020","NO","Supply",5400,"V-20050",21,3,6,12,"B","High")
m("1000-10067007","10067007","Hydraulic Accumulator Bladder Type 10L","MRO-HYD","Hydraulics","84790000","NO","Supply",18000,"V-20050",35,1,2,3,"A","Critical")
m("1000-10067008","10067008","Quick Coupling Flat Face 1/2in Male","MRO-HYD","Hydraulics","73079990","NO","Supply",480,"V-20058",7,20,40,80,"C","Low")
m("1000-10067009","10067009","Hydraulic Seal Kit for Cylinder 80mm","MRO-HYD","Hydraulics","40169300","SET","Supply",2800,"V-20050",14,5,10,20,"B","High")
m("1000-10067010","10067010","Flow Control Valve 3/4in Adjustable","MRO-HYD","Hydraulics","84812090","NO","Supply",3600,"V-20050",21,3,6,12,"B","Medium")

# ── MRO-LUB  Lubricants & Greases (10) ──────────────────────────────────────
m("1000-10078001","10078001","Servo 68 Hydraulic Oil 210L Drum","MRO-LUB","Lubricants & Greases","27101990","DR","Supply",14200,"V-20051",7,5,10,15,"B","High",1)
m("1000-10078002","10078002","EP Grease NLGI-2 15kg Pail","MRO-LUB","Lubricants & Greases","27101990","KG","Supply",3800,"V-20051",7,10,20,30,"C","Low",1)
m("1000-10078003","10078003","Turbine Oil 46 200L Drum","MRO-LUB","Lubricants & Greases","27101990","DR","Supply",16800,"V-20051",7,3,6,10,"B","High",1)
m("1000-10078004","10078004","Gear Oil EP 220 200L Drum","MRO-LUB","Lubricants & Greases","27101990","DR","Supply",15500,"V-20051",7,4,8,12,"B","High",1)
m("1000-10078005","10078005","Compressor Oil 46 20L Can","MRO-LUB","Lubricants & Greases","27101990","CAN","Supply",2800,"V-20051",7,10,20,30,"C","Medium",1)
m("1000-10078006","10078006","Mould Release Oil 20L Can","MRO-LUB","Lubricants & Greases","27101990","CAN","Supply",3200,"V-20051",7,8,16,24,"C","Medium",1)
m("1000-10078007","10078007","Chain Lubricant Spray 500ml","MRO-LUB","Lubricants & Greases","27101990","CAN","Supply",480,"V-20059",5,30,60,120,"C","Low",1)
m("1000-10078008","10078008","Anti-Seize Compound 500g Tin","MRO-LUB","Lubricants & Greases","34029090","TIN","Supply",860,"V-20059",7,20,40,80,"C","Low",1)
m("1000-10078009","10078009","High Temperature Grease NLGI-2 1kg","MRO-LUB","Lubricants & Greases","27101990","KG","Supply",1200,"V-20051",7,15,30,60,"C","Medium",1)
m("1000-10078010","10078010","Way Oil 68 20L Can","MRO-LUB","Lubricants & Greases","27101990","CAN","Supply",2600,"V-20051",7,10,20,30,"C","Low",1)

# ── MRO-WLD  Welding Consumables (10) ───────────────────────────────────────
m("1000-10089001","10089001","Welding Rod E6013 3.15mm 25kg","MRO-WLD","Welding Consumables","83111000","KG","Supply",2100,"V-20052",5,20,50,100,"B","Medium")
m("1000-10089002","10089002","MIG Wire ER70S-6 1.2mm 15kg Spool","MRO-WLD","Welding Consumables","83111000","KG","Supply",1650,"V-20052",5,15,30,60,"B","Medium")
m("1000-10089003","10089003","Welding Rod E7018 3.15mm 25kg","MRO-WLD","Welding Consumables","83111000","KG","Supply",2600,"V-20052",5,15,30,60,"B","Medium")
m("1000-10089004","10089004","SS Welding Rod 308L 2.5mm 5kg","MRO-WLD","Welding Consumables","83111000","KG","Supply",8500,"V-20052",7,5,10,20,"B","High")
m("1000-10089005","10089005","Tungsten Electrode 2.4mm 10-Pack","MRO-WLD","Welding Consumables","83112000","PKT","Supply",3200,"V-20052",7,10,20,40,"C","Medium")
m("1000-10089006","10089006","CO2 Gas Cylinder 30kg","MRO-WLD","Welding Consumables","28112900","CYL","Supply",1800,"V-20060",3,5,10,15,"B","High")
m("1000-10089007","10089007","Argon Gas Cylinder 8.8m3","MRO-WLD","Welding Consumables","28042100","CYL","Supply",2400,"V-20060",3,4,8,12,"B","High")
m("1000-10089008","10089008","Welding Gloves Leather Heavy Duty Pair","MRO-WLD","Welding Consumables","39262000","PAIR","Supply",320,"V-20061",3,50,100,200,"C","Low")
m("1000-10089009","10089009","Welding Helmet Auto-Darkening","MRO-WLD","Welding Consumables","90049090","NO","Supply",2800,"V-20061",7,5,10,20,"C","Medium")
m("1000-10089010","10089010","Anti-Spatter Spray 500ml Can","MRO-WLD","Welding Consumables","32089090","CAN","Supply",380,"V-20059",3,30,60,120,"C","Low",1)

# ── MRO-GAK  Gaskets & Seals (10) ───────────────────────────────────────────
m("1000-10091001","10091001","Spiral Wound Gasket 150mm ASME B16.20","MRO-GAK","Gaskets & Seals","84841000","NO","Supply",1850,"V-20062",14,20,40,80,"B","High")
m("1000-10091002","10091002","Ring Joint Gasket R-24 Octagonal","MRO-GAK","Gaskets & Seals","84841000","NO","Supply",2200,"V-20062",14,10,20,40,"B","High")
m("1000-10091003","10091003","PTFE Sheet 3mm 1000x1000mm","MRO-GAK","Gaskets & Seals","39169000","NO","Supply",4500,"V-20062",10,5,10,15,"C","Medium")
m("1000-10091004","10091004","O-Ring 50mm ID x 3.5mm NBR 70","MRO-GAK","Gaskets & Seals","40169300","PKT","Supply",240,"V-20062",7,30,60,120,"C","Low")
m("1000-10091005","10091005","Mechanical Seal Type 2100 25mm Shaft","MRO-GAK","Gaskets & Seals","84841000","NO","Supply",6800,"V-20062",21,3,6,12,"B","High")
m("1000-10091006","10091006","Graphite Rope Packing 12mm 5m","MRO-GAK","Gaskets & Seals","68159900","M","Supply",1200,"V-20062",7,10,20,40,"C","Medium")
m("1000-10091007","10091007","Rubber Sheet 5mm 1m x 1m Natural","MRO-GAK","Gaskets & Seals","40081190","NO","Supply",1800,"V-20063",7,5,10,20,"C","Low")
m("1000-10091008","10091008","Silicone Sealant RTV 300ml Tube","MRO-GAK","Gaskets & Seals","32091000","NO","Supply",580,"V-20063",5,20,40,80,"C","Low",1)
m("1000-10091009","10091009","V-Ring Seal 50mm Shaft","MRO-GAK","Gaskets & Seals","40169300","NO","Supply",420,"V-20062",7,20,40,80,"C","Medium")
m("1000-10091010","10091010","Lip Seal 80x100x12 NBR","MRO-GAK","Gaskets & Seals","40169300","NO","Supply",680,"V-20062",10,15,30,60,"C","Medium")

# ── MRO-BLT  Belts Chains & Couplings (10) ──────────────────────────────────
m("1000-10093001","10093001","V-Belt B-75 (17x1905mm)","MRO-BLT","Belts Chains & Couplings","40103100","NO","Supply",680,"V-20064",7,20,40,80,"B","High")
m("1000-10093002","10093002","Roller Chain 16B-1 5m","MRO-BLT","Belts Chains & Couplings","73151200","M","Supply",2400,"V-20064",10,10,20,30,"B","High")
m("1000-10093003","10093003","Flexible Coupling Jaw Type 65mm","MRO-BLT","Belts Chains & Couplings","84831000","NO","Supply",4800,"V-20064",14,5,10,15,"B","High")
m("1000-10093004","10093004","Timing Belt 5M-500-25","MRO-BLT","Belts Chains & Couplings","40103100","NO","Supply",1200,"V-20064",7,10,20,40,"C","Medium")
m("1000-10093005","10093005","Fluid Coupling 37kW (Voith or equiv)","MRO-BLT","Belts Chains & Couplings","84830000","NO","Supply",85000,"V-20064",60,1,1,2,"A","Critical")
m("1000-10093006","10093006","Gear Coupling Size 3 Rigid","MRO-BLT","Belts Chains & Couplings","84831000","NO","Supply",12500,"V-20064",28,2,4,6,"B","High")
m("1000-10093007","10093007","Chain Connector Link 16B","MRO-BLT","Belts Chains & Couplings","73151200","NO","Supply",180,"V-20064",5,50,100,200,"C","Low")
m("1000-10093008","10093008","Poly-V Belt 6PK1270","MRO-BLT","Belts Chains & Couplings","40103100","NO","Supply",1800,"V-20065",7,10,20,40,"C","Medium")
m("1000-10093009","10093009","Disc Coupling 45mm Aluminium","MRO-BLT","Belts Chains & Couplings","84831000","NO","Supply",3400,"V-20064",14,5,10,20,"C","Medium")
m("1000-10093010","10093010","Taper Lock Bush 1610 x 25mm","MRO-BLT","Belts Chains & Couplings","84831000","NO","Supply",560,"V-20064",7,20,40,80,"C","Low")

# ── MRO-FAS  Fasteners & Hardware (10) ──────────────────────────────────────
m("1000-10095001","10095001","HT Bolt M20x80 8.8 Grade Hex Head","MRO-FAS","Fasteners & Hardware","73181500","KG","Supply",180,"V-20053",3,50,100,200,"C","Low")
m("1000-10095002","10095002","HT Nut M20 8.8 Grade Hex","MRO-FAS","Fasteners & Hardware","73182900","KG","Supply",160,"V-20053",3,50,100,200,"C","Low")
m("1000-10095003","10095003","Spring Washer M20 Zinc Plated","MRO-FAS","Fasteners & Hardware","73182200","KG","Supply",120,"V-20053",3,50,100,200,"C","Low")
m("1000-10095004","10095004","U-Bolt M16 x 200mm Galvanised","MRO-FAS","Fasteners & Hardware","73181500","NO","Supply",280,"V-20053",5,30,60,120,"C","Low")
m("1000-10095005","10095005","Allen Key Set 1.5-10mm 9pc","MRO-FAS","Fasteners & Hardware","82042000","SET","Supply",480,"V-20066",5,10,20,40,"C","Low")
m("1000-10095006","10095006","Foundation Bolt M24x400 with Nut","MRO-FAS","Fasteners & Hardware","73181500","NO","Supply",420,"V-20053",5,20,40,80,"C","Low")
m("1000-10095007","10095007","Stainless Bolt M12x50 A2-70","MRO-FAS","Fasteners & Hardware","73181500","NO","Supply",28,"V-20053",5,100,200,400,"C","Low")
m("1000-10095008","10095008","Eye Bolt M20 Galvanised","MRO-FAS","Fasteners & Hardware","73181500","NO","Supply",380,"V-20053",5,20,40,80,"C","Low")
m("1000-10095009","10095009","Anchor Bolt M16 Chemical Type 150mm","MRO-FAS","Fasteners & Hardware","73181500","NO","Supply",240,"V-20066",7,30,60,120,"C","Low")
m("1000-10095010","10095010","Grub Screw M8x10 Class 45H Cup Point","MRO-FAS","Fasteners & Hardware","73181500","KG","Supply",580,"V-20053",3,20,40,80,"C","Low")

# ── MRO-PNM  Pneumatics (10) ────────────────────────────────────────────────
m("1000-10097001","10097001","Air Cylinder 63mm Bore 200mm Stroke","MRO-PNM","Pneumatics","84121100","NO","Supply",4200,"V-20067",14,5,10,15,"B","High")
m("1000-10097002","10097002","Solenoid Valve 5/2 Way 1/4in BSP","MRO-PNM","Pneumatics","84812040","NO","Supply",2800,"V-20067",14,5,10,20,"B","High")
m("1000-10097003","10097003","FRL Unit 1/2in BSP (Filter+Regulator+Lubricator)","MRO-PNM","Pneumatics","84813000","NO","Supply",3600,"V-20067",14,3,6,12,"B","High")
m("1000-10097004","10097004","Air Regulator 1/2in 0-10 Bar","MRO-PNM","Pneumatics","84813000","NO","Supply",1800,"V-20067",10,5,10,20,"C","Medium")
m("1000-10097005","10097005","Pneumatic Tubing 8mm OD 100m Roll","MRO-PNM","Pneumatics","39173200","M","Supply",1200,"V-20067",7,2,4,6,"C","Low")
m("1000-10097006","10097006","Push-in Fitting Elbow 8mm","MRO-PNM","Pneumatics","73079990","NO","Supply",180,"V-20067",5,50,100,200,"C","Low")
m("1000-10097007","10097007","Air Cylinder Seal Kit 63mm","MRO-PNM","Pneumatics","40169300","SET","Supply",1200,"V-20067",7,5,10,20,"C","Medium")
m("1000-10097008","10097008","Pressure Gauge 0-10 Bar 100mm Dial","MRO-PNM","Pneumatics","90262000","NO","Supply",980,"V-20068",7,10,20,40,"C","Low")
m("1000-10097009","10097009","Pneumatic Silencer 1/2in BSP","MRO-PNM","Pneumatics","84814000","NO","Supply",320,"V-20067",5,20,40,80,"C","Low")
m("1000-10097010","10097010","Air Preparation Unit 3/4in BSP","MRO-PNM","Pneumatics","84813000","NO","Supply",5200,"V-20067",21,2,4,6,"B","Medium")

# ── MRO-FLT  Filters & Strainers (10) ───────────────────────────────────────
m("1000-10099001","10099001","Oil Filter Element LF3349 (Fleetguard equiv)","MRO-FLT","Filters & Strainers","84212300","NO","Supply",480,"V-20058",7,20,40,80,"B","High")
m("1000-10099002","10099002","Air Filter Element AF1735 (Fleetguard equiv)","MRO-FLT","Filters & Strainers","84213900","NO","Supply",620,"V-20058",7,15,30,60,"B","High")
m("1000-10099003","10099003","Hydraulic Return Line Filter 10 Micron","MRO-FLT","Filters & Strainers","84219900","NO","Supply",1800,"V-20058",14,10,20,40,"B","High")
m("1000-10099004","10099004","Bag Filter Housing 10in Single","MRO-FLT","Filters & Strainers","84219900","NO","Supply",8500,"V-20068",21,2,4,6,"C","Medium")
m("1000-10099005","10099005","Basket Strainer 2in 150# Carbon Steel","MRO-FLT","Filters & Strainers","84219990","NO","Supply",6200,"V-20068",21,2,4,6,"C","Medium")
m("1000-10099006","10099006","Magnetic Filter Separator 1in BSP","MRO-FLT","Filters & Strainers","84219990","NO","Supply",4800,"V-20068",14,2,4,8,"B","Medium")
m("1000-10099007","10099007","Dust Collector Filter Bag 150mm x 3000mm","MRO-FLT","Filters & Strainers","84219990","NO","Supply",2200,"V-20068",14,10,20,40,"B","High")
m("1000-10099008","10099008","Fuel Filter Element FF5018","MRO-FLT","Filters & Strainers","84212300","NO","Supply",380,"V-20058",5,20,40,80,"C","Medium")
m("1000-10099009","10099009","Coalescing Filter Element 0.01 Micron","MRO-FLT","Filters & Strainers","84219900","NO","Supply",2800,"V-20058",14,5,10,20,"B","High")
m("1000-10099010","10099010","Y-Strainer 1.5in 150# SS316","MRO-FLT","Filters & Strainers","84219990","NO","Supply",3800,"V-20068",14,3,6,12,"C","Medium")

# ── MRO-INS  Instrumentation & Sensors (10) ─────────────────────────────────
m("1000-10101001","10101001","Thermocouple Type K 6mm x 150mm","MRO-INS","Instrumentation & Sensors","90330000","NO","Supply",1200,"V-20069",14,10,20,40,"B","High")
m("1000-10101002","10101002","RTD PT100 4-Wire 6mm x 200mm","MRO-INS","Instrumentation & Sensors","90330000","NO","Supply",2800,"V-20069",14,5,10,20,"B","High")
m("1000-10101003","10101003","Temperature Transmitter 4-20mA HART","MRO-INS","Instrumentation & Sensors","90330000","NO","Supply",8500,"V-20069",21,3,6,12,"A","Critical")
m("1000-10101004","10101004","Pressure Transmitter 0-100 Bar 4-20mA","MRO-INS","Instrumentation & Sensors","90262000","NO","Supply",12000,"V-20069",21,3,6,12,"A","Critical")
m("1000-10101005","10101005","Level Sensor Ultrasonic 4-20mA 5m Range","MRO-INS","Instrumentation & Sensors","90261000","NO","Supply",18000,"V-20069",28,2,4,6,"A","Critical")
m("1000-10101006","10101006","Flow Meter Electromagnetic 50mm","MRO-INS","Instrumentation & Sensors","90261000","NO","Supply",45000,"V-20069",42,1,2,3,"A","Critical")
m("1000-10101007","10101007","Vibration Sensor 4-20mA 0-25mm/s","MRO-INS","Instrumentation & Sensors","90319090","NO","Supply",9800,"V-20069",21,3,6,12,"B","High")
m("1000-10101008","10101008","Speed Sensor Hall Effect 5-24V","MRO-INS","Instrumentation & Sensors","90329090","NO","Supply",3200,"V-20069",14,5,10,20,"B","High")
m("1000-10101009","10101009","Thermowell 316SS 1/2in NPT 150mm","MRO-INS","Instrumentation & Sensors","90330000","NO","Supply",1800,"V-20069",10,5,10,20,"C","Medium")
m("1000-10101010","10101010","Multi-Function Relay Timer 11-Pin 230V","MRO-INS","Instrumentation & Sensors","85363000","NO","Supply",1400,"V-20049",10,10,20,40,"C","Medium")

# ── MRO-PPE  Safety & PPE (10) ──────────────────────────────────────────────
m("1000-10103001","10103001","Safety Helmet Type 1 HDPE Yellow","MRO-PPE","Safety & PPE","65119090","NO","Supply",380,"V-20061",3,50,100,200,"C","Low")
m("1000-10103002","10103002","Safety Shoes Steel Toe S3 Size 8","MRO-PPE","Safety & PPE","64011000","PAIR","Supply",1800,"V-20061",7,20,40,80,"C","Low")
m("1000-10103003","10103003","Safety Harness Full Body EN361","MRO-PPE","Safety & PPE","62114290","NO","Supply",3200,"V-20061",7,10,20,40,"B","Medium")
m("1000-10103004","10103004","Nitrile Gloves Medium Box 100","MRO-PPE","Safety & PPE","40151900","BOX","Supply",320,"V-20061",3,50,100,200,"C","Low")
m("1000-10103005","10103005","Safety Goggle Indirect Vent Clear","MRO-PPE","Safety & PPE","90049090","NO","Supply",280,"V-20061",3,50,100,200,"C","Low")
m("1000-10103006","10103006","N95 Respirator Mask Box 20","MRO-PPE","Safety & PPE","63079090","BOX","Supply",480,"V-20061",3,50,100,200,"B","High")
m("1000-10103007","10103007","High-Vis Vest Class 2 Yellow L","MRO-PPE","Safety & PPE","62114290","NO","Supply",280,"V-20061",3,100,200,400,"C","Low")
m("1000-10103008","10103008","Ear Plug NRR-33 Box 200 Pairs","MRO-PPE","Safety & PPE","90219000","BOX","Supply",480,"V-20061",3,20,40,80,"C","Low")
m("1000-10103009","10103009","Fall Arrester Self-Retracting 6m","MRO-PPE","Safety & PPE","62114290","NO","Supply",8500,"V-20061",14,5,10,20,"B","High")
m("1000-10103010","10103010","Chemical Splash Suit Category 3 Type 6","MRO-PPE","Safety & PPE","62114290","NO","Supply",2400,"V-20061",7,10,20,40,"B","High")

# ── MRO-PMP  Pumps & Pump Parts (10) ────────────────────────────────────────
m("1000-10105001","10105001","Centrifugal Pump 50x40-200 11kW","MRO-PMP","Pumps & Pump Parts","84137000","NO","Supply",62000,"V-20070",42,1,2,3,"A","Critical")
m("1000-10105002","10105002","Submersible Pump 5.5kW 3-Phase","MRO-PMP","Pumps & Pump Parts","84137000","NO","Supply",48000,"V-20070",35,1,2,3,"A","Critical")
m("1000-10105003","10105003","Pump Impeller SS316 100mm","MRO-PMP","Pumps & Pump Parts","84139190","NO","Supply",8500,"V-20070",21,2,4,6,"B","High")
m("1000-10105004","10105004","Pump Mechanical Seal 35mm Shaft","MRO-PMP","Pumps & Pump Parts","84841000","NO","Supply",4200,"V-20062",14,3,6,12,"B","High")
m("1000-10105005","10105005","Pump Casing Wear Ring SS316 100mm","MRO-PMP","Pumps & Pump Parts","84139190","NO","Supply",3800,"V-20070",21,2,4,6,"B","High")
m("1000-10105006","10105006","Gear Pump KP0/2.5 D04 Hydraulic","MRO-PMP","Pumps & Pump Parts","84136010","NO","Supply",12000,"V-20050",28,2,4,6,"B","High")
m("1000-10105007","10105007","Diaphragm Pump 1in AODD","MRO-PMP","Pumps & Pump Parts","84137000","NO","Supply",22000,"V-20070",21,1,2,3,"B","High")
m("1000-10105008","10105008","Pump Bearing Set (Pair) 6205+6305","MRO-PMP","Pumps & Pump Parts","84829100","SET","Supply",1800,"V-20045",14,5,10,20,"B","High")
m("1000-10105009","10105009","Pump Shaft Seal Packing Rope 12mm","MRO-PMP","Pumps & Pump Parts","84841000","M","Supply",1400,"V-20062",7,5,10,20,"C","Medium")
m("1000-10105010","10105010","Peristaltic Pump Head 25mm Chemical","MRO-PMP","Pumps & Pump Parts","84137000","NO","Supply",18500,"V-20070",35,1,2,3,"B","High")

# ── MRO-VLV  Valves & Actuators (10) ────────────────────────────────────────
m("1000-10107001","10107001","Gate Valve 2in 150# Carbon Steel RF","MRO-VLV","Valves & Actuators","84818090","NO","Supply",4200,"V-20071",14,3,6,12,"B","High")
m("1000-10107002","10107002","Ball Valve 1in Full Bore SS316 Screwed","MRO-VLV","Valves & Actuators","84818090","NO","Supply",2800,"V-20071",7,5,10,20,"B","High")
m("1000-10107003","10107003","Butterfly Valve 4in 150# CS Wafer","MRO-VLV","Valves & Actuators","84818090","NO","Supply",6500,"V-20071",14,3,6,10,"B","High")
m("1000-10107004","10107004","Check Valve 1.5in 150# Swing Type","MRO-VLV","Valves & Actuators","84818090","NO","Supply",3200,"V-20071",10,5,10,15,"C","Medium")
m("1000-10107005","10107005","Globe Valve 1in 150# CS Body","MRO-VLV","Valves & Actuators","84818090","NO","Supply",2600,"V-20071",10,5,10,20,"C","Medium")
m("1000-10107006","10107006","Pneumatic Actuator Double Acting 100mm","MRO-VLV","Valves & Actuators","84121100","NO","Supply",8500,"V-20067",21,2,4,6,"B","High")
m("1000-10107007","10107007","Safety Relief Valve 1in 150# Set 6 Bar","MRO-VLV","Valves & Actuators","84818090","NO","Supply",5800,"V-20071",21,3,6,12,"B","High")
m("1000-10107008","10107008","Needle Valve 1/4in SS316 Screwed","MRO-VLV","Valves & Actuators","84818090","NO","Supply",1600,"V-20071",7,10,20,40,"C","Low")
m("1000-10107009","10107009","Solenoid Valve 2/2 Way 1in 24VDC","MRO-VLV","Valves & Actuators","84812040","NO","Supply",7200,"V-20072",14,3,6,10,"B","High")
m("1000-10107010","10107010","Pinch Valve 3in 150# Pneumatic","MRO-VLV","Valves & Actuators","84818090","NO","Supply",22000,"V-20072",35,1,2,3,"A","Critical")

# ── MRO-GRD  Grinding & Abrasives (10) ──────────────────────────────────────
m("1000-10109001","10109001","Grinding Wheel 230mm x 6mm x 22mm A24","MRO-GRD","Grinding & Abrasives","68042210","NO","Supply",280,"V-20073",3,50,100,200,"B","High")
m("1000-10109002","10109002","Cutting Disc 230mm x 2mm x 22mm A36","MRO-GRD","Grinding & Abrasives","68042210","NO","Supply",180,"V-20073",3,100,200,400,"B","High")
m("1000-10109003","10109003","Flap Disc 115mm Zirconia 40G","MRO-GRD","Grinding & Abrasives","68042210","NO","Supply",220,"V-20073",3,100,200,400,"C","Medium")
m("1000-10109004","10109004","Wire Brush Wheel 150mm Twisted","MRO-GRD","Grinding & Abrasives","96032910","NO","Supply",380,"V-20073",3,30,60,120,"C","Low")
m("1000-10109005","10109005","Bench Grinding Wheel 200mm A60","MRO-GRD","Grinding & Abrasives","68042210","NO","Supply",480,"V-20073",5,20,40,80,"C","Low")
m("1000-10109006","10109006","Diamond Blade 350mm for Concrete","MRO-GRD","Grinding & Abrasives","82079090","NO","Supply",3800,"V-20073",7,5,10,20,"B","Medium")
m("1000-10109007","10109007","Emery Cloth Roll 50mm x 50m 80G","MRO-GRD","Grinding & Abrasives","68052030","M","Supply",4200,"V-20073",5,2,4,6,"C","Low")
m("1000-10109008","10109008","Strip Disc 115mm Paint Removal","MRO-GRD","Grinding & Abrasives","68042210","NO","Supply",320,"V-20073",3,50,100,200,"C","Low")
m("1000-10109009","10109009","Angle Grinder Depressed Centre Disc T27","MRO-GRD","Grinding & Abrasives","68042210","NO","Supply",140,"V-20073",3,100,200,400,"C","Low")
m("1000-10109010","10109010","Scotch-Brite Hand Pad 6x9in Box 20","MRO-GRD","Grinding & Abrasives","68052030","BOX","Supply",480,"V-20073",3,20,40,80,"C","Low")

# ── MRO-RFT  Refractories (steel-specific) (10) ─────────────────────────────
m("1000-10111001","10111001","High Alumina Brick 70% Al2O3 Std Size","MRO-RFT","Refractories","69022010","NO","Supply",480,"V-20074",21,200,500,1000,"A","Critical")
m("1000-10111002","10111002","Castable Refractory 70% Al2O3 50kg Bag","MRO-RFT","Refractories","69022090","KG","Supply",85,"V-20074",14,500,1000,2000,"A","Critical",1)
m("1000-10111003","10111003","Refractory Mortar High Temp 25kg Bag","MRO-RFT","Refractories","69022090","KG","Supply",52,"V-20074",10,500,1000,2000,"B","High",1)
m("1000-10111004","10111004","Magnesia Carbon Brick 10% C Converter","MRO-RFT","Refractories","69022010","NO","Supply",1200,"V-20074",28,500,1000,2000,"A","Critical")
m("1000-10111005","10111005","Ceramic Fibre Blanket 50mm 128kg/m3 Roll","MRO-RFT","Refractories","69031090","M","Supply",1800,"V-20074",14,10,20,40,"B","High")
m("1000-10111006","10111006","Silica Brick 96% SiO2 Coke Oven Grade","MRO-RFT","Refractories","69022010","NO","Supply",380,"V-20074",21,200,500,1000,"A","Critical")
m("1000-10111007","10111007","Insulation Brick K-23 2300°F","MRO-RFT","Refractories","69022010","NO","Supply",280,"V-20074",21,200,500,1000,"B","High")
m("1000-10111008","10111008","Ramming Mass Silica 25kg Bag","MRO-RFT","Refractories","69022090","KG","Supply",38,"V-20075",7,1000,2000,4000,"A","Critical",1)
m("1000-10111009","10111009","Ceramic Fibre Module 200mm x 300mm","MRO-RFT","Refractories","69031090","NO","Supply",2800,"V-20074",21,50,100,200,"B","High")
m("1000-10111010","10111010","Gunning Mix 70% Al2O3 25kg Bag","MRO-RFT","Refractories","69022090","KG","Supply",95,"V-20075",7,500,1000,2000,"A","Critical",1)

# ── MRO-ELC  Electrodes & Arc Consumables (10) ──────────────────────────────
m("1000-10113001","10113001","Carbon Electrode 300mm x 1800mm RP Grade","MRO-ELC","Electrodes & Arc Consumables","85452000","NO","Supply",8500,"V-20076",21,10,20,40,"A","Critical")
m("1000-10113002","10113002","Carbon Electrode 350mm x 1800mm HP Grade","MRO-ELC","Electrodes & Arc Consumables","85452000","NO","Supply",12000,"V-20076",21,10,20,40,"A","Critical")
m("1000-10113003","10113003","Electrode Nipple 300mm for Carbon Electrode","MRO-ELC","Electrodes & Arc Consumables","85452000","NO","Supply",3200,"V-20076",21,10,20,40,"A","Critical")
m("1000-10113004","10113004","Electrode Holder 400A Heavy Duty","MRO-ELC","Electrodes & Arc Consumables","85169090","NO","Supply",1800,"V-20052",7,10,20,40,"B","High")
m("1000-10113005","10113005","Ground Clamp 500A with Cable 3m","MRO-ELC","Electrodes & Arc Consumables","85169090","NO","Supply",1200,"V-20052",7,10,20,40,"B","Medium")
m("1000-10113006","10113006","Plasma Cutting Nozzle 1.1mm 10-Pack","MRO-ELC","Electrodes & Arc Consumables","84620000","PKT","Supply",2400,"V-20052",7,10,20,40,"B","High")
m("1000-10113007","10113007","Plasma Electrode Hafnium 10-Pack","MRO-ELC","Electrodes & Arc Consumables","84620000","PKT","Supply",3600,"V-20052",7,10,20,40,"B","High")
m("1000-10113008","10113008","MIG Contact Tip 1.2mm M6 Thread Box 50","MRO-ELC","Electrodes & Arc Consumables","83111000","BOX","Supply",680,"V-20052",5,10,20,40,"B","High")
m("1000-10113009","10113009","Flux Core Wire E71T-1 1.2mm 15kg Spool","MRO-ELC","Electrodes & Arc Consumables","83111000","KG","Supply",3200,"V-20052",7,10,20,40,"B","High")
m("1000-10113010","10113010","Submerged Arc Flux 25kg Bag","MRO-ELC","Electrodes & Arc Consumables","83112000","KG","Supply",2800,"V-20052",10,20,40,80,"B","High")

# ── MRO-PLT  Structural & Plates (10) ───────────────────────────────────────
m("1000-10115001","10115001","MS Plate IS2062 E250 12mm 2500x1250","MRO-PLT","Structural & Plates","72083710","NO","Supply",8200,"V-20077",7,5,10,20,"B","High")
m("1000-10115002","10115002","MS Angle 75x75x8mm 6m Length","MRO-PLT","Structural & Plates","72163100","NO","Supply",2800,"V-20077",5,10,20,40,"C","Medium")
m("1000-10115003","10115003","MS Channel 150x75mm 6m Length","MRO-PLT","Structural & Plates","72162100","NO","Supply",4200,"V-20077",5,5,10,20,"C","Medium")
m("1000-10115004","10115004","MS Round Bar 50mm Dia 3m","MRO-PLT","Structural & Plates","72141000","NO","Supply",3600,"V-20077",5,5,10,20,"C","Medium")
m("1000-10115005","10115005","SS316L Sheet 3mm 2000x1000","MRO-PLT","Structural & Plates","72193310","NO","Supply",28000,"V-20077",14,2,4,6,"B","High")
m("1000-10115006","10115006","Chequered Plate MS 6mm 2500x1250","MRO-PLT","Structural & Plates","72085110","NO","Supply",9800,"V-20077",7,3,6,10,"C","Medium")
m("1000-10115007","10115007","ERW Pipe 2in Schedule 40 6m CS","MRO-PLT","Structural & Plates","73064010","NO","Supply",3200,"V-20077",7,5,10,20,"B","High")
m("1000-10115008","10115008","MS Flat 50x10mm 6m Length","MRO-PLT","Structural & Plates","72169900","NO","Supply",1600,"V-20077",5,10,20,40,"C","Low")
m("1000-10115009","10115009","GI Pipe 1in Schedule 40 6m","MRO-PLT","Structural & Plates","73063010","NO","Supply",2800,"V-20077",5,5,10,20,"C","Low")
m("1000-10115010","10115010","H-Beam ISMB 200mm 6m","MRO-PLT","Structural & Plates","72163200","NO","Supply",12500,"V-20077",7,2,4,8,"B","Medium")

# ── MRO-CAB  Cables & Wiring (10) ───────────────────────────────────────────
m("1000-10117001","10117001","Power Cable 4-Core 16mm2 XLPE/SWA 100m","MRO-CAB","Cables & Wiring","85442000","M","Supply",28500,"V-20078",14,1,2,3,"A","Critical")
m("1000-10117002","10117002","Control Cable 4-Core 2.5mm2 XLPE 100m","MRO-CAB","Cables & Wiring","85442000","M","Supply",12500,"V-20078",14,2,4,6,"B","High")
m("1000-10117003","10117003","Instrument Cable 2-Pair 1.5mm2 Shielded 100m","MRO-CAB","Cables & Wiring","85442000","M","Supply",9800,"V-20078",14,2,4,6,"B","High")
m("1000-10117004","10117004","Cable Gland M25 Brass IP68","MRO-CAB","Cables & Wiring","85369090","NO","Supply",280,"V-20078",5,50,100,200,"C","Low")
m("1000-10117005","10117005","Cable Tray Perforated 100mm x 3m","MRO-CAB","Cables & Wiring","73182900","NO","Supply",1200,"V-20078",7,10,20,40,"C","Low")
m("1000-10117006","10117006","Cable Lug Copper 16mm2 M8 Crimping","MRO-CAB","Cables & Wiring","85369090","NO","Supply",28,"V-20078",3,200,400,800,"C","Low")
m("1000-10117007","10117007","Heat Shrink Tubing 12mm x 1m","MRO-CAB","Cables & Wiring","39173200","M","Supply",120,"V-20079",3,100,200,400,"C","Low")
m("1000-10117008","10117008","Conduit PVC 25mm x 3m","MRO-CAB","Cables & Wiring","39172390","NO","Supply",280,"V-20079",3,50,100,200,"C","Low")
m("1000-10117009","10117009","Flexible Conduit Metallic 20mm x 10m","MRO-CAB","Cables & Wiring","83079000","M","Supply",1400,"V-20079",5,10,20,40,"C","Low")
m("1000-10117010","10117010","Power Cable 1-Core 95mm2 XLPE 100m","MRO-CAB","Cables & Wiring","85442000","M","Supply",42000,"V-20078",21,1,2,3,"A","Critical")

# ── CAP-MOT  Motors & Drives (Capital) (8) ──────────────────────────────────
m("1000-10201001","10201001","TEFC Motor 15kW 4-Pole 415V IE3","CAP-MOT","Motors & Drives","85011010","NO","Capital",62000,"V-20080",42,1,1,2,"A","Critical")
m("1000-10201002","10201002","TEFC Motor 37kW 4-Pole 415V IE3","CAP-MOT","Motors & Drives","85011010","NO","Capital",145000,"V-20080",42,1,1,2,"A","Critical")
m("1000-10201003","10201003","TEFC Motor 75kW 4-Pole 415V IE3","CAP-MOT","Motors & Drives","85011010","NO","Capital",285000,"V-20080",56,1,1,1,"A","Critical")
m("1000-10201004","10201004","VFD Drive 22kW 415V ABB ACS580","CAP-MOT","Motors & Drives","85044000","NO","Capital",98000,"V-20049",56,1,1,2,"A","Critical")
m("1000-10201005","10201005","VFD Drive 55kW 415V ABB ACS880","CAP-MOT","Motors & Drives","85044000","NO","Capital",220000,"V-20049",56,1,1,1,"A","Critical")
m("1000-10201006","10201006","Servo Drive 5kW with Encoder","CAP-MOT","Motors & Drives","85044000","NO","Capital",185000,"V-20049",70,1,1,1,"A","Critical")
m("1000-10201007","10201007","TEFC Motor 5.5kW 6-Pole 415V IE3","CAP-MOT","Motors & Drives","85011010","NO","Capital",28000,"V-20080",35,1,2,3,"B","High")
m("1000-10201008","10201008","Soft Starter 45kW 415V 3-Phase","CAP-MOT","Motors & Drives","85044000","NO","Capital",78000,"V-20049",42,1,1,2,"A","Critical")

# ── CAP-TRF  Transformers & Switchgear (Capital) (8) ─────────────────────────
m("1000-10203001","10203001","Distribution Transformer 250 kVA 11kV/433V","CAP-TRF","Transformers & Switchgear","85042300","NO","Capital",480000,"V-20081",84,1,0,1,"A","Critical")
m("1000-10203002","10203002","Distribution Transformer 500 kVA 11kV/433V","CAP-TRF","Transformers & Switchgear","85042300","NO","Capital",850000,"V-20081",84,1,0,1,"A","Critical")
m("1000-10203003","10203003","ACB 4-Pole 1600A 415V Motorised","CAP-TRF","Transformers & Switchgear","85352910","NO","Capital",185000,"V-20081",56,1,1,2,"A","Critical")
m("1000-10203004","10203004","ACB 4-Pole 3200A 415V Motorised","CAP-TRF","Transformers & Switchgear","85352910","NO","Capital",320000,"V-20081",56,1,0,1,"A","Critical")
m("1000-10203005","10203005","VCB 11kV 630A Vacuum Circuit Breaker","CAP-TRF","Transformers & Switchgear","85352110","NO","Capital",280000,"V-20081",84,1,0,1,"A","Critical")
m("1000-10203006","10203006","MCC Panel 415V 8-Way Fabricated","CAP-TRF","Transformers & Switchgear","85371090","NO","Capital",650000,"V-20081",90,1,0,1,"A","Critical")
m("1000-10203007","10203007","PLC Siemens S7-1500 CPU with I/O","CAP-TRF","Transformers & Switchgear","84714900","NO","Capital",380000,"V-20082",90,1,0,1,"A","Critical")
m("1000-10203008","10203008","UPS 20 kVA Online Double Conversion","CAP-TRF","Transformers & Switchgear","85044000","NO","Capital",220000,"V-20082",42,1,1,2,"A","Critical")

# ── CAP-PMP  Pumps & Compressors Capital (6) ─────────────────────────────────
m("1000-10205001","10205001","Screw Air Compressor 75kW 10 Bar","CAP-PMP","Pumps & Compressors Capital","84141010","NO","Capital",850000,"V-20083",84,1,0,1,"A","Critical")
m("1000-10205002","10205002","Reciprocating Air Compressor 37kW 15 Bar","CAP-PMP","Pumps & Compressors Capital","84141010","NO","Capital",480000,"V-20083",84,1,0,1,"A","Critical")
m("1000-10205003","10205003","Process Pump 100-80-200 55kW","CAP-PMP","Pumps & Compressors Capital","84137000","NO","Capital",380000,"V-20070",70,1,0,1,"A","Critical")
m("1000-10205004","10205004","High Pressure Pump 250 Bar 7.5kW","CAP-PMP","Pumps & Compressors Capital","84137000","NO","Capital",285000,"V-20070",70,1,0,1,"A","Critical")
m("1000-10205005","10205005","Nitrogen Generator PSA 50 Nm3/hr","CAP-PMP","Pumps & Compressors Capital","84419000","NO","Capital",1250000,"V-20083",120,1,0,1,"A","Critical")
m("1000-10205006","10205006","Cooling Tower Fan Drive 22kW","CAP-PMP","Pumps & Compressors Capital","84191100","NO","Capital",180000,"V-20083",56,1,0,1,"A","Critical")

# ── SRV-MNT  Maintenance Services (6) ───────────────────────────────────────
m("1000-10301001","10301001","Alignment Service — Precision Laser","SRV-MNT","Maintenance Services","99851100","SRV","Service",18000,"V-20084",2,1,0,1,"B","High")
m("1000-10301002","10301002","Balancing Service — Dynamic In-situ","SRV-MNT","Maintenance Services","99851100","SRV","Service",25000,"V-20084",3,1,0,1,"B","High")
m("1000-10301003","10301003","Predictive Maintenance — Vibration Analysis","SRV-MNT","Maintenance Services","99851900","SRV","Service",45000,"V-20084",1,1,0,1,"B","High")
m("1000-10301004","10301004","Annual Maintenance Contract — Cranes","SRV-MNT","Maintenance Services","99851100","SRV","Service",480000,"V-20085",7,1,0,1,"A","Critical")
m("1000-10301005","10301005","Annual Maintenance Contract — Compressors","SRV-MNT","Maintenance Services","99851100","SRV","Service",320000,"V-20085",7,1,0,1,"A","Critical")
m("1000-10301006","10301006","Shutdown Maintenance — BF Repair","SRV-MNT","Maintenance Services","99851900","SRV","Service",2500000,"V-20085",30,1,0,1,"A","Critical")

# ── SRV-CIV  Civil & Structural (4) ─────────────────────────────────────────
m("1000-10303001","10303001","Civil Works — Flooring Repair Plant","SRV-CIV","Civil & Structural","99532100","SRV","Service",180000,"V-20086",14,1,0,1,"B","Medium")
m("1000-10303002","10303002","Civil Works — Cooling Tower Painting","SRV-CIV","Civil & Structural","99532100","SRV","Service",320000,"V-20086",14,1,0,1,"B","Medium")
m("1000-10303003","10303003","Civil Works — Drain Construction","SRV-CIV","Civil & Structural","99532100","SRV","Service",650000,"V-20086",21,1,0,1,"B","Medium")
m("1000-10303004","10303004","Civil Works — Building Renovation","SRV-CIV","Civil & Structural","99532100","SRV","Service",1200000,"V-20086",30,1,0,1,"A","High")

# ── SRV-TRN  Transport & Logistics (4) ──────────────────────────────────────
m("1000-10305001","10305001","Truck Hire 10T — Intra-Plant","SRV-TRN","Transport & Logistics","99603100","SRV","Service",12000,"V-20087",1,1,0,1,"C","Low")
m("1000-10305002","10305002","Crane Hire — 50T Mobile","SRV-TRN","Transport & Logistics","99603100","SRV","Service",45000,"V-20087",1,1,0,1,"B","High")
m("1000-10305003","10305003","Annual Scrap Transport Contract","SRV-TRN","Transport & Logistics","99603100","SRV","Service",1800000,"V-20087",14,1,0,1,"B","Medium")
m("1000-10305004","10305004","Rail Wagon Loading — Monthly Contract","SRV-TRN","Transport & Logistics","99603100","SRV","Service",280000,"V-20087",7,1,0,1,"B","Medium")

# ── MRO-CHM  Chemicals (6) ──────────────────────────────────────────────────
m("1000-10119001","10119001","Pickling Acid HCl 32% 250L Drum","MRO-CHM","Chemicals","28061020","DR","Supply",8500,"V-20088",5,5,10,15,"A","Critical",1)
m("1000-10119002","10119002","Caustic Soda NaOH 48% 250L Drum","MRO-CHM","Chemicals","28151200","DR","Supply",12000,"V-20088",5,3,6,10,"A","Critical",1)
m("1000-10119003","10119003","Rust Remover / Phosphoric Acid 50L Can","MRO-CHM","Chemicals","28092000","CAN","Supply",4200,"V-20088",5,5,10,20,"B","High",1)
m("1000-10119004","10119004","Industrial Degreaser Solvent 25L Can","MRO-CHM","Chemicals","34029090","CAN","Supply",3800,"V-20059",5,5,10,20,"B","Medium",1)
m("1000-10119005","10119005","Descaling Chemical for Boiler 25kg","MRO-CHM","Chemicals","38209000","KG","Supply",4800,"V-20088",7,5,10,20,"B","High",1)
m("1000-10119006","10119006","Water Treatment Chemical Antiscalant 25L","MRO-CHM","Chemicals","38099200","CAN","Supply",5500,"V-20088",7,5,10,15,"B","High",1)

print(f"Total materials prepared: {len(materials)}")

c.executemany("INSERT INTO Material_Master VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", materials)
conn.commit()
print(f"✅ Material_Master: {c.execute('SELECT COUNT(*) FROM Material_Master').fetchone()[0]} rows")
conn.close()
