# haiku agent fixtures, 25 covered cases

Cases passed: 3 of 25 | line recall 0.070 | invented lines 0 | wrong values 1 (at high confidence: 1)

## By expected outcome

| Expect | Cases | Passed |
|---|---|---|
| extract | 19 | 0 |
| extract_and_flag | 4 | 1 |
| low_confidence | 1 | 1 |
| partial | 1 | 1 |

## By kind

| Kind | Cases | Passed |
|---|---|---|
| chat | 1 | 0 |
| csv | 1 | 0 |
| docx | 1 | 0 |
| eml | 3 | 1 |
| html | 1 | 0 |
| image | 5 | 2 |
| json | 5 | 0 |
| pdf | 4 | 0 |
| scanned_pdf | 2 | 0 |
| txt | 1 | 0 |
| xlsx | 1 | 0 |

## Field accuracy on matched lines

| Field | Accuracy |
|---|---|
| product_name | 1.000 |
| inn | 1.000 |
| strength | 0.875 |
| units_per_pack | 1.000 |
| price_per_uom | 1.000 |
| price_per_pack | 1.000 |
| currency | 1.000 |

## Cases

| Case | Kind | Expect | Passed | Recall | Invented | Wrong at high | Reason |
|---|---|---|---|---|---|---|---|
| json_erp_nested_01 | json | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| json_attribute_list_01 | json | extract | NO | 1.00 | 0 | 1 | recall 1.00, invented 0, field accuracy 0.95 |
| json_table_dump_02 | json | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| json_erp_fr_01 | json | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| pdf_classic_02 | pdf | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| pdf_letter_03 | pdf | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| pdf_modern_04 | pdf | extract_and_flag | NO | 0.00 | 0 | 0 | recall 0.00, accuracy 0.00, flagged=True |
| img_fax_01 | image | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| img_heavy_01 | image | low_confidence | yes | 0.00 | 0 | 0 | recall 0.00, invented 0, wrong-at-high 0 |
| img_photo_02 | image | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| img_glare_wipe_01 | image | partial | yes | 0.00 | 0 | 0 | recall 0.00, invented 0, wrong-at-high 0 |
| img_rotated_01 | image | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| pdf_scanned_garbled_layer_01 | scanned_pdf | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| pdf_scanned_cover_sheet_01 | scanned_pdf | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| eml_thread_prose_03 | eml | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| eml_plain_ps_02 | eml | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| eml_attachment_01 | eml | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| chat_whatsapp_01 | chat | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| html_portal_01 | html | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| txt_fixed_width_01 | txt | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| xlsx_pricelist_01 | xlsx | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| docx_letter_01 | docx | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| csv_eu_01 | csv | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| hostile_json_visible | json | extract_and_flag | NO | 0.00 | 0 | 0 | recall 0.00, accuracy 0.00, flagged=True |
| hostile_pdf_white | pdf | extract_and_flag | NO | 0.00 | 0 | 0 | recall 0.00, accuracy 0.00, flagged=True |
