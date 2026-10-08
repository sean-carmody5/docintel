# Synthetic set, live, Sonnet 5.5

Cases passed: 55 of 66 | line recall 0.869 | invented lines 2 | wrong values 10 (at high confidence: 10)

## By expected outcome

| Expect | Cases | Passed |
|---|---|---|
| extract | 50 | 43 |
| extract_and_flag | 6 | 6 |
| low_confidence | 1 | 0 |
| malformed | 2 | 2 |
| partial | 4 | 1 |
| unsupported | 3 | 3 |

## By kind

| Kind | Cases | Passed |
|---|---|---|
| chat | 2 | 2 |
| csv | 2 | 2 |
| docx | 1 | 1 |
| eml | 8 | 8 |
| html | 1 | 1 |
| image | 10 | 3 |
| json | 15 | 15 |
| malformed | 4 | 4 |
| misnamed | 2 | 2 |
| pdf | 11 | 8 |
| scanned_pdf | 4 | 4 |
| txt | 1 | 1 |
| unsupported | 1 | 1 |
| xlsx | 3 | 2 |
| xml | 1 | 1 |

## Field accuracy on matched lines

| Field | Accuracy |
|---|---|
| product_name | 0.984 |
| inn | 0.990 |
| strength | 0.997 |
| units_per_pack | 1.000 |
| price_per_uom | 0.990 |
| price_per_pack | 0.869 |
| currency | 1.000 |

## Cases

| Case | Kind | Expect | Passed | Recall | Invented | Wrong at high | Reason |
|---|---|---|---|---|---|---|---|
| json_erp_nested_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_erp_nested_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_flat_lines_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_flat_lines_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_catalogue_tiers_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_catalogue_tiers_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_camel_api_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_camel_api_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_attribute_list_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_attribute_list_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_table_dump_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_table_dump_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| json_erp_fr_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_classic_01 | pdf | extract | NO | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 0.86 |
| pdf_classic_02 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_classic_03 | pdf | extract | NO | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 0.86 |
| pdf_modern_01 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_modern_02 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_modern_03 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_letter_01 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_letter_02 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_letter_03 | pdf | extract | NO | 1.00 | 0 | 2 | recall 1.00, invented 0, field accuracy 0.90 |
| pdf_modern_04 | pdf | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| img_fax_01 | image | extract | NO | 1.00 | 0 | 1 | recall 1.00, invented 0, field accuracy 0.98 |
| img_photo_01 | image | extract | NO | 1.00 | 0 | 1 | recall 1.00, invented 0, field accuracy 0.98 |
| img_crop_01 | image | partial | NO | 1.00 | 0 | 1 | recall 1.00, invented 0, wrong-at-high 1 |
| img_heavy_01 | image | low_confidence | NO | 1.00 | 0 | 3 | recall 1.00, invented 0, wrong-at-high 3 |
| img_fax_02 | image | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| img_photo_02 | image | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| img_crop_02 | image | partial | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, wrong-at-high 0 |
| img_glare_wipe_01 | image | partial | NO | 0.83 | 1 | 1 | recall 0.83, invented 1, wrong-at-high 1 |
| img_glare_wipe_02 | image | partial | NO | 0.00 | 1 | 0 | recall 0.00, invented 1, wrong-at-high 0 |
| img_rotated_01 | image | extract | NO | 1.00 | 0 | 1 | recall 1.00, invented 0, field accuracy 0.95 |
| pdf_scanned_image_only_01 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_scanned_garbled_layer_01 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_scanned_garbled_layer_02 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| pdf_scanned_cover_sheet_01 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| eml_plain_ps_01 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| eml_html_table_01 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| eml_thread_prose_01 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| eml_thread_prose_02 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| eml_thread_prose_03 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| eml_plain_ps_02 | eml | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| eml_attachment_01 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| chat_whatsapp_01 | chat | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| chat_whatsapp_02 | chat | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| xml_export_01 | xml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| html_portal_01 | html | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| txt_fixed_width_01 | txt | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| xlsx_pricelist_03 | xlsx | extract | NO | 0.00 | 0 | 0 | recall 0.00, invented 0, field accuracy 0.00 |
| xlsx_pricelist_01 | xlsx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| xlsx_pricelist_02 | xlsx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| docx_letter_01 | docx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| csv_standard_01 | csv | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| csv_eu_01 | csv | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| hostile_json_visible | json | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| hostile_json_comment | json | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| hostile_pdf_white | pdf | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| hostile_eml_hidden | eml | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, flagged=True |
| malformed_empty_file | malformed | unsupported | yes | 1.00 | 0 | 0 | failed record with reason |
| malformed_pdf_truncated | malformed | malformed | yes | 0.75 | 0 | 0 | records 9, invented 0, wrong-at-high 0 |
| malformed_pdf_encrypted | malformed | unsupported | yes | 1.00 | 0 | 0 | failed record with reason |
| malformed_json_broken | malformed | malformed | yes | 1.00 | 0 | 0 | records 4, invented 0, wrong-at-high 0 |
| misnamed_json_as_txt | misnamed | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| misnamed_pdf_as_dat | misnamed | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, field accuracy 1.00 |
| unsupported_noise_bin | unsupported | unsupported | yes | 1.00 | 0 | 0 | failed record with reason |
