# replay-haiku-synth, final pipeline

Cases passed: 60 of 66 | line recall 0.957 | invented lines 12 | wrong values 27 (at high confidence: 4, flagged for a person: 23)

## By expected outcome

| Expect | Cases | Passed |
|---|---|---|
| extract | 50 | 46 |
| extract_and_flag | 6 | 6 |
| low_confidence | 1 | 0 |
| malformed | 2 | 2 |
| partial | 4 | 3 |
| unsupported | 3 | 3 |

## By kind

| Kind | Cases | Passed |
|---|---|---|
| chat | 2 | 2 |
| csv | 2 | 2 |
| docx | 1 | 1 |
| eml | 8 | 8 |
| html | 1 | 1 |
| image | 10 | 5 |
| json | 15 | 15 |
| malformed | 4 | 4 |
| misnamed | 2 | 2 |
| pdf | 11 | 10 |
| scanned_pdf | 4 | 4 |
| txt | 1 | 1 |
| unsupported | 1 | 1 |
| xlsx | 3 | 3 |
| xml | 1 | 1 |

## Field accuracy on matched lines

| Field | Accuracy |
|---|---|
| product_name | 0.955 |
| inn | 1.000 |
| strength | 0.994 |
| units_per_pack | 1.000 |
| price_per_uom | 0.979 |
| price_per_pack | 0.979 |
| currency | 1.000 |

## Cases

| Case | Kind | Expect | Passed | Recall | Invented | Wrong at high | Reason |
|---|---|---|---|---|---|---|---|
| json_erp_nested_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_erp_nested_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_flat_lines_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_flat_lines_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_catalogue_tiers_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_catalogue_tiers_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_camel_api_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_camel_api_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_attribute_list_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_attribute_list_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_table_dump_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_table_dump_02 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| json_erp_fr_01 | json | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_classic_01 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_classic_02 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_classic_03 | pdf | extract | NO | 1.00 | 0 | 1 | recall 1.00, invented 0, accuracy 0.99, wrong-at-high 1, flagged wrong 0 |
| pdf_modern_01 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_modern_02 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_modern_03 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_letter_01 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_letter_02 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_letter_03 | pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_modern_04 | pdf | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, wrong-at-high 0, flagged=True |
| img_fax_01 | image | extract | NO | 0.67 | 2 | 2 | recall 0.67, invented 2, accuracy 0.79, wrong-at-high 2, flagged wrong 4 |
| img_photo_01 | image | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 0.93, wrong-at-high 0, flagged wrong 3 |
| img_crop_01 | image | partial | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, wrong-at-high 0 |
| img_heavy_01 | image | low_confidence | NO | 0.00 | 3 | 0 | recall 0.00, invented 3, wrong-at-high 0 |
| img_fax_02 | image | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 0.71, wrong-at-high 0, flagged wrong 2 |
| img_photo_02 | image | extract | NO | 1.00 | 0 | 1 | recall 1.00, invented 0, accuracy 0.93, wrong-at-high 1, flagged wrong 4 |
| img_crop_02 | image | partial | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, wrong-at-high 0 |
| img_glare_wipe_01 | image | partial | NO | 0.67 | 2 | 0 | recall 0.67, invented 2, wrong-at-high 0 |
| img_glare_wipe_02 | image | partial | yes | 0.00 | 0 | 0 | recall 0.00, invented 0, wrong-at-high 0 |
| img_rotated_01 | image | extract | NO | 0.00 | 5 | 0 | recall 0.00, invented 5, accuracy 0.00, wrong-at-high 0, flagged wrong 0 |
| pdf_scanned_image_only_01 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 0.98, wrong-at-high 0, flagged wrong 1 |
| pdf_scanned_garbled_layer_01 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_scanned_garbled_layer_02 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| pdf_scanned_cover_sheet_01 | scanned_pdf | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 0.98, wrong-at-high 0, flagged wrong 1 |
| eml_plain_ps_01 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| eml_html_table_01 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| eml_thread_prose_01 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| eml_thread_prose_02 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| eml_thread_prose_03 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| eml_plain_ps_02 | eml | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, wrong-at-high 0, flagged=True |
| eml_attachment_01 | eml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| chat_whatsapp_01 | chat | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| chat_whatsapp_02 | chat | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| xml_export_01 | xml | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| html_portal_01 | html | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| txt_fixed_width_01 | txt | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| xlsx_pricelist_03 | xlsx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| xlsx_pricelist_01 | xlsx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| xlsx_pricelist_02 | xlsx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| docx_letter_01 | docx | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| csv_standard_01 | csv | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| csv_eu_01 | csv | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| hostile_json_visible | json | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, wrong-at-high 0, flagged=True |
| hostile_json_comment | json | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, wrong-at-high 0, flagged=True |
| hostile_pdf_white | pdf | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, wrong-at-high 0, flagged=True |
| hostile_eml_hidden | eml | extract_and_flag | yes | 1.00 | 0 | 0 | recall 1.00, accuracy 1.00, wrong-at-high 0, flagged=True |
| malformed_empty_file | malformed | unsupported | yes | 1.00 | 0 | 0 | failed record with reason |
| malformed_pdf_truncated | malformed | malformed | yes | 0.75 | 0 | 0 | records 9, invented 0, wrong-at-high 0 |
| malformed_pdf_encrypted | malformed | unsupported | yes | 1.00 | 0 | 0 | failed record with reason |
| malformed_json_broken | malformed | malformed | yes | 1.00 | 0 | 0 | records 4, invented 0, wrong-at-high 0 |
| misnamed_json_as_txt | misnamed | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| misnamed_pdf_as_dat | misnamed | extract | yes | 1.00 | 0 | 0 | recall 1.00, invented 0, accuracy 1.00, wrong-at-high 0, flagged wrong 0 |
| unsupported_noise_bin | unsupported | unsupported | yes | 1.00 | 0 | 0 | failed record with reason |
