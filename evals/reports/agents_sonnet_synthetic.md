# sonnet agent fixtures, 24 covered cases

Cases passed: 24 of 24 | line recall 1.000 | invented lines 0 | wrong values 0 (at high confidence: 0)

## By expected outcome

| Expect | Cases | Passed |
|---|---|---|
| extract | 18 | 18 |
| extract_and_flag | 4 | 4 |
| low_confidence | 1 | 1 |
| partial | 1 | 1 |

## By kind

| Kind | Cases | Passed |
|---|---|---|
| chat | 1 | 1 |
| csv | 1 | 1 |
| docx | 1 | 1 |
| eml | 2 | 2 |
| html | 1 | 1 |
| image | 5 | 5 |
| json | 5 | 5 |
| pdf | 4 | 4 |
| scanned_pdf | 2 | 2 |
| txt | 1 | 1 |
| xlsx | 1 | 1 |

## Field accuracy on matched lines

| Field | Accuracy |
|---|---|
| product_name | 1.000 |
| inn | 0.991 |
| strength | 0.982 |
| units_per_pack | 0.991 |
| price_per_uom | 0.964 |
| price_per_pack | 0.964 |
| currency | 1.000 |

## Cases

| Case | Kind | Expect | Passed | Recall | Invented | Wrong at high | Reason |
|---|---|---|---|---|---|---|---|
| json_erp_nested_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_attribute_list_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_table_dump_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_erp_fr_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_classic_02 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_letter_03 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_modern_04 | pdf | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| img_fax_01 | image | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| img_heavy_01 | image | low_confidence | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, wrong-at-high 0 |
| img_photo_02 | image | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| img_glare_wipe_01 | image | partial | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, wrong-at-high 0 |
| img_rotated_01 | image | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_scanned_garbled_layer_01 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_scanned_cover_sheet_01 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| eml_thread_prose_03 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| eml_plain_ps_02 | eml | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| chat_whatsapp_01 | chat | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| html_portal_01 | html | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| txt_fixed_width_01 | txt | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| xlsx_pricelist_01 | xlsx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| docx_letter_01 | docx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| csv_eu_01 | csv | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| hostile_json_visible | json | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| hostile_pdf_white | pdf | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
