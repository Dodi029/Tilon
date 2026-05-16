# Text Layer Quality Report

## Summary

- v3.0 대비 현재 변경사항을 비교하기 위해 none/OCR/DOM/DOM+OCR 네 모드를 같은 샘플에 적용했다.
- 단순 글자 수가 아니라 필수 문구 exact match와 섞임 marker를 함께 판단했다.
- 현재 Notion URL 테스트는 `CURRENT_NOTION_URL` 환경변수가 없으면 실행하지 않는다.

## Results

| sample | mode | pages | chars | required | strict | broken | status | dom_items | ocr_words |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: |
| short_html | none | 1 | 0 | 0/5 | 0/4 | no | disabled | 0 | 0 |
| short_html | ocr | 1 | 172 | 4/5 | 1/4 | no | applied | 0 | 24 |
| short_html | dom | 1 | 164 | 5/5 | 1/4 | no | applied | 5 | 0 |
| short_html | hybrid | 1 | 164 | 5/5 | 1/4 | no | applied | 5 | 0 |
| mixed_html | none | 1 | 0 | 0/5 | 0/4 | no | disabled | 0 | 0 |
| mixed_html | ocr | 1 | 1994 | 4/5 | 0/4 | no | applied | 0 | 404 |
| mixed_html | dom | 1 | 1808 | 5/5 | 4/4 | no | applied | 31 | 0 |
| mixed_html | hybrid | 1 | 2326 | 5/5 | 4/4 | no | applied | 31 | 77 |
| html_upload | none | 1 | 0 | 0/5 | 0/4 | no | disabled | 0 | 0 |
| html_upload | ocr | 1 | 821 | 4/5 | 0/4 | no | applied | 0 | 170 |
| html_upload | dom | 1 | 734 | 5/5 | 4/4 | no | applied | 13 | 0 |
| html_upload | hybrid | 1 | 910 | 5/5 | 4/4 | no | applied | 13 | 29 |

## Required Text Checks

### short_html / none
- 종료 시 바로 프로비전 가능: MISS
- MasterVD2: MISS
- Hyper-V: MISS
- C:\ClusterStorage: MISS
- PowerShell: MISS
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: MISS
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: MISS
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: MISS
- C:\ClusterStorage\Volume1\MasterVD2: MISS
- broken sentence marker: OK

### short_html / ocr
- 종료 시 바로 프로비전 가능: MISS
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: MISS
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: MISS
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: MISS
- C:\ClusterStorage\Volume1\MasterVD2: OK
- broken sentence marker: OK

### short_html / dom
- 종료 시 바로 프로비전 가능: OK
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: MISS
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: MISS
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: MISS
- C:\ClusterStorage\Volume1\MasterVD2: OK
- broken sentence marker: OK

### short_html / hybrid
- 종료 시 바로 프로비전 가능: OK
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: MISS
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: MISS
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: MISS
- C:\ClusterStorage\Volume1\MasterVD2: OK
- broken sentence marker: OK

### mixed_html / none
- 종료 시 바로 프로비전 가능: MISS
- MasterVD2: MISS
- Hyper-V: MISS
- C:\ClusterStorage: MISS
- PowerShell: MISS
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: MISS
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: MISS
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: MISS
- C:\ClusterStorage\Volume1\MasterVD2: MISS
- broken sentence marker: OK

### mixed_html / ocr
- 종료 시 바로 프로비전 가능: MISS
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: MISS
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: MISS
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: MISS
- C:\ClusterStorage\Volume1\MasterVD2: MISS
- broken sentence marker: OK

### mixed_html / dom
- 종료 시 바로 프로비전 가능: OK
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: OK
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: OK
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: OK
- C:\ClusterStorage\Volume1\MasterVD2: OK
- broken sentence marker: OK

### mixed_html / hybrid
- 종료 시 바로 프로비전 가능: OK
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: OK
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: OK
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: OK
- C:\ClusterStorage\Volume1\MasterVD2: OK
- broken sentence marker: OK

### html_upload / none
- 종료 시 바로 프로비전 가능: MISS
- MasterVD2: MISS
- Hyper-V: MISS
- C:\ClusterStorage: MISS
- PowerShell: MISS
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: MISS
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: MISS
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: MISS
- C:\ClusterStorage\Volume1\MasterVD2: MISS
- broken sentence marker: OK

### html_upload / ocr
- 종료 시 바로 프로비전 가능: MISS
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: MISS
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: MISS
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: MISS
- C:\ClusterStorage\Volume1\MasterVD2: MISS
- broken sentence marker: OK

### html_upload / dom
- 종료 시 바로 프로비전 가능: OK
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: OK
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: OK
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: OK
- C:\ClusterStorage\Volume1\MasterVD2: OK
- broken sentence marker: OK

### html_upload / hybrid
- 종료 시 바로 프로비전 가능: OK
- MasterVD2: OK
- Hyper-V: OK
- C:\ClusterStorage: OK
- PowerShell: OK
- ENS-NS-HOST01(물리 운영서버01)의 Hyper-V에서 MasterVD2 세팅 완료 후 VD 종료 시 바로 프로비전 가능: OK
- 처음부터 HOST01 서버에 MasterVD2를 생성하여 복사/덮어쓰기 과정 불필요: OK
- MasterVD2 : MasterVD.vhdx를 실행하는 새로운 컴퓨터: OK
- C:\ClusterStorage\Volume1\MasterVD2: OK
- broken sentence marker: OK

## Judgment

- mode average score: {'none': 0.0, 'ocr': 46.666666666666664, 'dom': 110.0, 'hybrid': 110.0}
- best measured mode: dom
- default recommendation: hybrid. DOM text is preferred, OCR is used only as a supplemental layer for non-DOM/image text, and overlapping OCR should be excluded.
- current Notion URL test: SKIPPED because CURRENT_NOTION_URL was not provided.
