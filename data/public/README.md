# Public sample documents

Real price lists, catalogues and request-for-quotation forms, used as robustness
smoke tests. They carry no ground truth. The pipeline is expected to degrade into
flags on them, never to crash and never to guess with confidence.

Fetched by `uv run python -m evals.public.fetch`. Sources, licences and tags live in
`evals/public/sources.json`; `manifest.json` here records size, SHA-256 and fetch date.

## Licences

6 of 37 files are under an explicit open licence (CC BY, CC BY-NC with
attribution, Open Jordanian Licence) and are committed. The rest state no licence or
assert all rights reserved (MSH, Ghana NHIS) and are fetched on demand, never
redistributed, not even in a private repository. Three government hosts serve broken
certificate chains and are fetched with verification off; they are marked in the sources file.

| Document | Publisher | Format | Size | Tags | Licence | Committed |
|---|---|---|---|---|---|---|
| Global Fund PPM reference pricing, ARVs Q1 2026 | The Global Fund | pdf | 163 KB | prices, tabular, usd | CC BY-NC 4.0 (The Global Fund). Attribution: The Global Fund to Fight AIDS, Tuberculosis and Malaria. | yes |
| Global Fund PPM reference pricing, HIV strategic medicines | The Global Fund | pdf | 138 KB | prices, tabular, usd | CC BY-NC 4.0 (The Global Fund). Attribution: The Global Fund to Fight AIDS, Tuberculosis and Malaria. | yes |
| UNICEF Supply Division DTP vaccine price data | UNICEF | pdf | 108 KB | prices, tabular, usd, cold_chain | None stated; unicef.org terms | no, fetch on demand |
| UNICEF antimalarial medicines price data, May 2026 | UNICEF | pdf | 76 KB | prices, tabular, usd, price_range | None stated; unicef.org terms | no, fetch on demand |
| UNICEF RUTF price data 2003 to 2026 | UNICEF | pdf | 134 KB | prices, tabular, usd | None stated; unicef.org terms | no, fetch on demand |
| PAHO Strategic Fund reference prices, June 2026 | PAHO | pdf | 646 KB | prices, tabular, usd, wide_table, price_range, long | Prices FCA, not guaranteed, not a formal proposal | no, fetch on demand |
| PAHO Strategic Fund LTA price list, October 2022 | PAHO | pdf | 418 KB | prices, tabular, usd, bilingual | None stated | no, fetch on demand |
| USAID GHSC-PSM product e-catalog, June 2026 | USAID GHSC-PSM | pdf | 4466 KB | prices, tabular, usd, long, large | Prices are estimates and may not be current | no, fetch on demand |
| MSH International Medical Products Price Guide 2015 | Management Sciences for Health | pdf | 3457 KB | prices, tabular, usd, long, large, multilingual | Copyright MSH, all rights reserved. Do not redistribute. | no, fetch on demand |
| WHO AFRO essential medicines price indicator 2007 | WHO AFRO | pdf | 532 KB | prices, tabular, usd, long, incoterms | None stated | no, fetch on demand |
| CHAI ARV reference price list 2016 | Clinton Health Access Initiative | pdf | 269 KB | prices, tabular, usd, footnotes | None stated | no, fetch on demand |
| MSF Untangling the Web of ARV price reductions, 14th edition | MSF Access Campaign | pdf | 2625 KB | prices, narrative, usd, long | None stated | no, fetch on demand |
| South Africa NDoH contract circular HP07-2026DAI | South Africa National Department of Health | pdf | 1118 KB | prices, tabular, zar, long, awards | None stated | no, fetch on demand |
| Tanzania MSD price catalogue 2018/19 | Medical Stores Department Tanzania, via openAFRICA | pdf | 1646 KB | prices, tabular, tzs, long, terms_preamble | CC BY (openAFRICA). Attribution: Medical Stores Department, Tanzania, via openAFRICA. | yes |
| Ghana NHIS medicines list 2025 | National Health Insurance Authority, Ghana | pdf | 1166 KB | prices, tabular, ghs, long | All rights reserved. Do not redistribute. | no, fetch on demand |
| Jan Aushadhi MRP list, October 2015 | PMBI India | pdf | 561 KB | prices, tabular, inr | None stated | no, fetch on demand |
| DRAP Pakistan SRO 100(I)/2002 MRP schedule | Drug Regulatory Authority of Pakistan | pdf | 357 KB | prices, tabular, pkr, gazette | Government notification | no, fetch on demand |
| DRAP SRO 24(I)/2023, MRPs of 20 drugs | Drug Regulatory Authority of Pakistan | pdf | 107 KB | prices, scanned, pkr, bad_ocr_layer | Government notification | no, fetch on demand |
| DRAP SRO 1995(I)/2022 paracetamol MRP | Drug Regulatory Authority of Pakistan | pdf | 54 KB | prices, scanned, pkr, bad_ocr_layer | Government notification | no, fetch on demand |
| Quezon City RFQ for drugs and medicines, QCPC-24-DM-0178C | Quezon City Government, Philippines | pdf | 1455 KB | rfq, scanned, php, bad_ocr_layer, form | None stated | no, fetch on demand |
| GMC Baramati quotation form for drugs | Government Medical College Baramati, India | pdf | 767 KB | rfq, scanned, inr, bad_ocr_layer, form | None stated | no, fetch on demand |
| Mariveles Mental Wellness and General Hospital RFQ PR 2023-09-0604 | Department of Health, Philippines | pdf | 489 KB | rfq, prices, php, form | None stated | no, fetch on demand |
| PhilHealth 2011 annual procurement plan, drugs and medicines | PhilHealth | pdf | 484 KB | prices, tabular, php, messy_layout | None stated | no, fetch on demand |
| DBM Philippines RFQ 25-028, clinic medicines | Department of Budget and Management, Philippines | pdf | 403 KB | rfq, php, text_heavy, terms_preamble | None stated | no, fetch on demand |
| Ipca Laboratories domestic formulations price list, September 2025 | Ipca Laboratories | pdf | 349 KB | prices, tabular, inr, manufacturer, dense | None stated | no, fetch on demand |
| UNFPA Jordan RFQ 20/002 pharmaceuticals | UNFPA | pdf | 952 KB | rfq, no_prices, form | None stated | no, fetch on demand |
| South Africa database of medicine prices, 1 October 2026 | South Africa National Department of Health | xlsx | 3285 KB | prices, spreadsheet, zar, large | None stated | no, fetch on demand |
| WHO MI4A vaccine purchase dataset, September 2026 | WHO | xlsx | 2041 KB | prices, spreadsheet, usd, multi_sheet, incoterms | WHO terms; disclaimer in sheet 1 | no, fetch on demand |
| Sri Lanka SPC awarded pharmaceutical tenders, June 2026 | State Pharmaceuticals Corporation of Sri Lanka | xlsx | 30 KB | prices, spreadsheet, mixed_currency, multi_sheet, awards | None stated | no, fetch on demand |
| Jordan JFDA drug prices 2020 | JFDA via opendata.gov.jo | xlsx | 1257 KB | prices, spreadsheet, jod, misnamed_extension, arabic, large | Open Jordanian Licence. Attribution: Jordan Food and Drug Administration via opendata.gov.jo. | yes |
| Turkish Medicines Agency reference-based price list, February 2026 | TITCK | xlsx | 112 KB | prices, spreadsheet, eur, turkish | None stated | no, fetch on demand |
| KEMSA price list 2017 | KEMSA via openAFRICA | csv | 59 KB | prices, csv, kes | CC BY (openAFRICA). Attribution: KEMSA via openAFRICA / Code for Africa. | yes |
| Tanzania MSD price catalogue 2018/19, CSV | Medical Stores Department Tanzania, via openAFRICA | csv | 40 KB | prices, csv, tzs | CC BY (openAFRICA). Attribution: Medical Stores Department, Tanzania, via openAFRICA. | yes |
| Sri Lanka SPC tender board decisions, August 2012 | State Pharmaceuticals Corporation of Sri Lanka | doc | 198 KB | prices, legacy_office, usd, incoterms | None stated | no, fetch on demand |
| UNFPA Syria Annex 1 quotation form | UNFPA | docx | 59 KB | rfq, no_prices, form, docx | None stated | no, fetch on demand |
| IDA Foundation product indicator 2025/26 | IDA Foundation | pdf | 2664 KB | no_prices, catalogue, bilingual, long | None stated | no, fetch on demand |
| Joint Medical Store Uganda product catalogue, March 2026 | Joint Medical Store | xlsx | 301 KB | no_prices, catalogue, spreadsheet, multi_sheet, protected | None stated | no, fetch on demand |
