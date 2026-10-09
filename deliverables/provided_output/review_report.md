# Review report

Run: 2026-10-09T11:12:44+00:00 | extractor: model | model: anthropic:claude-sonnet-5-5 | input: data\provided

## At a glance

- Documents: 8 loaded, 0 failed to load
- Records: 37 (pending_review: 37)
- Needs review: 17 | clean: 20 | no lines or failed: 0
- Unit price confidence: high 31, medium 0, low 6
- Conflicts across suppliers: 3 | duplicate quotations: 1

## Look at these first

| Record | Document | Product | Unit price | Currency | Overall | Why |
|---|---|---|---|---|---|---|
| bcba6cb66af2d7c8:1 | scan_02_lowres_fax_andina_p1.png | Dolostop 500 |  | USD | 0.00 | price_per_uom: model could not read this field |
| 687ef24b38889f7b:1 | scan_03_glare_partial_andina_p1.jpg | Dolostop 500 |  | USD | 0.00 | price_per_uom: model could not read this field; units_per_pack: not stated; uom: model could not read this field |
| 687ef24b38889f7b:2 | scan_03_glare_partial_andina_p1.jpg | Amlodin 5 |  | USD | 0.00 | price_per_uom: model could not read this field; units_per_pack: model could not read this field; uom: model could not read this field |
| 687ef24b38889f7b:3 | scan_03_glare_partial_andina_p1.jpg | Losandina 50 |  | USD | 0.00 | price_per_uom: model could not read this field; uom: model could not read this field |
| 687ef24b38889f7b:4 | scan_03_glare_partial_andina_p1.jpg |  | 0.345 | USD | 0.00 | product_name: model could not read this field; units_per_pack: not stated |
| 687ef24b38889f7b:5 | scan_03_glare_partial_andina_p1.jpg |  | 0.0074 | USD | 0.00 | product_name: model could not read this field |
| 687ef24b38889f7b:6 | scan_03_glare_partial_andina_p1.jpg |  | 0.412 | USD | 0.00 | product_name: model could not read this field; units_per_pack: not stated |
| 4f98a2993aad8978:1 | RE_RFQ-2026-0244_Novara_quotation.eml | Azimax 250 | 0.134 | EUR | 0.45 | price_per_uom: derived from pack price and units per pack; price_per_uom corrected in the document from 0.128 to 0.134 |
| 4f98a2993aad8978:3 | RE_RFQ-2026-0244_Novara_quotation.eml | Dexafar 4 mg/mL | 0.41 | EUR | 0.45 | price_per_uom: derived from pack price and units per pack |
| 4f98a2993aad8978:2 | RE_RFQ-2026-0244_Novara_quotation.eml | Zincora 20 | 0.0155 | EUR | 0.95 | unit price derived, not stated |
| 6dbf066a71947643:1 | sanova_offer_export_2026-08-03.json | Sanotri-TLD | 0.035 | EUR | 0.95 | unit price derived, not stated |
| 6dbf066a71947643:2 | sanova_offer_export_2026-08-03.json | Sanofour Kit | 0.01253 | EUR | 0.95 | unit price derived, not stated |
| 6dbf066a71947643:3 | sanova_offer_export_2026-08-03.json | Sanodip 5 | 0.0104 | EUR | 0.95 | unit price derived, not stated |
| 59ff62da1c113cfb:1 | ubuntu_health_price_list_Q3-2026.json | Panadel 500 | 0.0415 | ZAR | 0.95 | tiered pricing; lowest-quantity tier shown |
| 59ff62da1c113cfb:2 | ubuntu_health_price_list_Q3-2026.json | Ubucef 1 g | 17.8 | ZAR | 0.95 | tiered pricing; lowest-quantity tier shown |
| 59ff62da1c113cfb:3 | ubuntu_health_price_list_Q3-2026.json | Misotab 200 | 1.6125 | ZAR | 0.95 | tiered pricing; lowest-quantity tier shown |
| 59ff62da1c113cfb:4 | ubuntu_health_price_list_Q3-2026.json | Ubuglar 100 | 122.4 | ZAR | 0.95 | tiered pricing; lowest-quantity tier shown |

## Same product, more than one supplier

| INN | Strength | Form | Suppliers | Currencies | Units/pack | Unit prices | Note |
|---|---|---|---|---|---|---|---|
| amoxicillin+clavulanic acid | 500 mg/125 mg | tablet | Mekong Pharma JSC, Zenith Pharma Laboratories Ltd. | USD, USD | 20, 14 | 0.0715, 0.0642 | same currency and unit; unit prices differ by 11% |
| dolutegravir+lamivudine+tenofovir | 300 mg/300 mg/50 mg | tablet | Mekong Pharma JSC, Sanova Laboratories Pvt. Ltd. | USD, EUR | 30, 90 | 0.0428, 0.035 | not directly comparable: different currencies, no FX applied |
| paracetamol | 500 mg | tablet | FARMACEUTICA ANDINA S.A.S., Ubuntu Health Manufacturing (Pty) Ltd | USD, ZAR | 20, 1000 | 0.0091, 0.0415 | not directly comparable: different currencies, no FX applied |

## Same quotation, more than one file

| Supplier | Reference | Files | Matched lines | Agreements | Disagreements |
|---|---|---|---|---|---|
| FARMACEUTICA ANDINA S.A.S. | FA-COT-2026-118 | farmaceutica_andina_proforma_FA-COT-2026-118.pdf, scan_02_lowres_fax_andina_p1.png, scan_03_glare_partial_andina_p1.jpg | 14 | 85 | 0 |

## Clean records

| Record | Document | Product | Unit price | Currency | Overall |
|---|---|---|---|---|---|
| d8c71b3365a6d381:1 | farmaceutica_andina_proforma_FA-COT-2026-118.pdf | Dolostop 500 | 0.0091 | USD | 1.00 |
| d8c71b3365a6d381:2 | farmaceutica_andina_proforma_FA-COT-2026-118.pdf | Amlodin 5 | 0.0128 | USD | 1.00 |
| d8c71b3365a6d381:3 | farmaceutica_andina_proforma_FA-COT-2026-118.pdf | Losandina 50 | 0.0205 | USD | 1.00 |
| d8c71b3365a6d381:4 | farmaceutica_andina_proforma_FA-COT-2026-118.pdf | Amoxidina 250/5 | 0.345 | USD | 0.85 |
| d8c71b3365a6d381:5 | farmaceutica_andina_proforma_FA-COT-2026-118.pdf | Enalten 10 | 0.0074 | USD | 1.00 |
| d8c71b3365a6d381:6 | farmaceutica_andina_proforma_FA-COT-2026-118.pdf | Salbudina 2/5 | 0.412 | USD | 0.85 |
| d987fde6989e14ea:1 | mekong_pharma_quotation_MKP-2026-0812.pdf | Mekamox 500/125 | 0.0715 | USD | 1.00 |
| d987fde6989e14ea:2 | mekong_pharma_quotation_MKP-2026-0812.pdf | Vermaben 400 | 0.0223 | USD | 1.00 |
| d987fde6989e14ea:3 | mekong_pharma_quotation_MKP-2026-0812.pdf | Salvent HFA | 1.42 | USD | 1.00 |
| d987fde6989e14ea:4 | mekong_pharma_quotation_MKP-2026-0812.pdf | Mekatri 300/300/50 | 0.0428 | USD | 1.00 |
| d987fde6989e14ea:5 | mekong_pharma_quotation_MKP-2026-0812.pdf | Ferrofol 60/0.4 | 0.00485 | USD | 1.00 |
| bcba6cb66af2d7c8:2 | scan_02_lowres_fax_andina_p1.png | Amlodin 5 | 0.0128 | USD | 0.90 |
| bcba6cb66af2d7c8:3 | scan_02_lowres_fax_andina_p1.png | Losandina 50 | 0.0205 | USD | 0.90 |
| bcba6cb66af2d7c8:4 | scan_02_lowres_fax_andina_p1.png | Amoxidina 250/5 | 0.345 | USD | 0.85 |
| bcba6cb66af2d7c8:5 | scan_02_lowres_fax_andina_p1.png | Enalten 10 | 0.0074 | USD | 0.90 |
| bcba6cb66af2d7c8:6 | scan_02_lowres_fax_andina_p1.png | Salbudina 2/5 | 0.412 | USD | 0.85 |
| 037c65509b9d2e1f:1 | zenith_pharma_quotation_ZPL-Q-2026-4471.json | Zenamox 500/125 | 0.0642 | USD | 1.00 |
| 037c65509b9d2e1f:2 | zenith_pharma_quotation_ZPL-Q-2026-4471.json | Artezen-20/120 | 0.0398 | USD | 1.00 |
| 037c65509b9d2e1f:3 | zenith_pharma_quotation_ZPL-Q-2026-4471.json | Metzen XR 1000 | 0.0215 | USD | 1.00 |
| 037c65509b9d2e1f:4 | zenith_pharma_quotation_ZPL-Q-2026-4471.json | Oxyzen 10 IU/mL | 0.128 | USD | 1.00 |
