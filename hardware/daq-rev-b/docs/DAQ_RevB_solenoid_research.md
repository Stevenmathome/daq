# DAQ Rev B - solenoid valve current research (checked 2026-11-22)

DC coils have no AC-style inrush; current = V/R = W/12 V. Design: 2.0 A/channel nominal, 2.15 A worst case, 14 A total (15.05 A worst case).

| Model | Coil W | I @ 12 V (A) | Inrush | Link |
|---|---|---|---|---|
| Beduan 1/4" nylon valve, 12 V (1kl-03900-WSV) | 3.0 | 0.25 (49 ohm) | none (DC) | https://www.amazon.com/Beduan-Plastic-Solenoid-Electric-Normally/dp/B07MX5489G |
| Beduan 1/2" plastic diaphragm valve (kl04440) | 4.3 | 0.315 | none (DC) | https://www.amazon.com/Beduan-Plastic-Electric-Solenoid-Water/dp/B07NWCRM75 |
| YIDAY 1/2" plastic FPD-270A (coil 26 ohm) | 5.5 | 0.46 (12/26; listed 0.30) | none (DC) | https://www.amazon.com/YIDAY-Normally-Plastic-Electric-Solenoid/dp/B07P95D61D |
| VNYERRNI 1/2" plastic valve | 8.0 | 0.60 | none (DC) | https://www.amazon.com/VNYERRNI-Electric-Solenoid-Magnetic-Normally/dp/B0DBFBZBM9 |
| Beduan 2ACK 1/4" anodized aluminium valve | 6.5 | 0.54 | none (DC) | https://www.amazon.com/Beduan-Normally-Closed-Electric-Solenoid/dp/B07N2LGFYS |
| Parker Skinner 7121KBN2SV00N0C111C1 1/4" brass | 10.0 | 0.83 | none (DC) | https://www.gghyd.com/7121kbn2sv00n0c111c1-parker-skinner-2-way-normally-closed-direct-acting-brass-solenoid-valve-12v-dc-conduit-housing.html |
| Heschen/Beduan 1/4" brass 2W-025-08 (15 VA) | 15.0 | 1.25 | none (DC) | https://www.amazon.com/Heschen-Electromagnetic-2W-025-08-Closing-Compressed/dp/B07284YRPF |
| ASCO 8210 series, coil 097617, 12 VDC (8210103) | 16.8 | 1.40 | none (DC) | https://kscdirect.com/itemDetail/6837574/8210103-csa-12-dc-dd-valve-solenoid-dc12-dc/ |
| U.S. Solid USS2-01017 1/2" brass semi-direct | 17.0 | 1.42 | none (DC) | https://ussolid.com/products/1-2-solenoid-valve-brass-12v-dc-normally-closed-with-viton-seal-html |
| U.S. Solid USS2-00012 1/2" brass semi-direct | 20.0 | 1.67 | none (DC) | https://ussolid.com/products/u-s-solid-electric-solenoid-valve-1-2-12v-dc-solenoid-valve-brass-body-normally-closed-viton-seal-html |
| U.S. Solid USS-NSV00003 1/2" brass direct lift | 22.0 | 1.83 (listed) | none (DC) | https://ussolid.com/products/u-s-solid-1-2-brass-electric-solenoid-valve-12v-dc-normally-closed-viton-air-water-oil-fuel-html |
| Parker Skinner 7121KBN2NV00N0L111C1 (leads coil) | 22.0 | 1.83 | none (DC) | https://www.gghyd.com/7121kbn2nv00n0l111c1-parker-skinner-2-way-normally-closed-1-4-npt-direct-acting-brass-solenoid-valve-12vdc-leads.html |
| Bosch 0 332 019 150 automotive 30 A relay (coil) | 1.6-2.2 | 0.13-0.18 (85 ohm eq.: 0.14) | none (DC) | http://www.mouser.com/catalog/specsheets/Bosch%20Relays.pdf |
