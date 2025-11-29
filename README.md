**돌파고 GUI**


다운로드 링크:

[https://drive.google.com/file/d/1gYMLynAMEK1KPPABlQsEc9GQRkxNehSP/view?usp=drive_link](https://drive.google.com/file/d/1Q-n_EWjQwkACPLuo0U7q6diNENvlK9DL/view?usp=sharing)

1) 압축을 푼 뒤 LostArk_Faceting_Bot.exe 를 더블클릭하여 실행
처음 실행 시 가능한 수많은 경우의 수를 계산하기 때문에 다소 시간이 소요됨

<img width="285" height="460" alt="image" src="https://github.com/user-attachments/assets/f1595dd2-2b10-4052-8792-04a78e9429ab" />

2) 메인 창에서 본인이 원하는 목표(97/96) 및 감소능력이 5+이상이어도 상관없는지를 체크

확률 계산이 완료되면 START버튼이 활성화됨

3) 메인 창에서 본인의 게임 세로 해상도 (1080P or 1440P) 에 해당하는 옵션을 체크

4) 반투명 오버레이 창의 O 위치들을 세공 위치(감소 능력까지) 에 정확히, 주황색 네모를 성공률 첫 번째 숫자에 정확히 맞춤

만약 UI가 미세하게 크거나 작을 경우 UI 스케일 < > 를 통해 미세 조정 가능

<img width="637" height="430" alt="image" src="https://github.com/user-attachments/assets/8d3a530a-5681-4730-a2d1-caf4ea9ae3b8" />

5) 메인 창의 START버튼을 누름

6) 맨 처음 돌에서 아무거나 누르면 잠시 후에 확률 계산 후 가장 최적의 선택지를 녹색으로 추천해줌
![GIF 2025-11-29 오후 12-39-40](https://github.com/user-attachments/assets/cc7d98f9-a494-4eb7-8ca8-c17afc83c774)

만약 노란색으로 추천된다면, 인식에 오류가 있을 가능성이 있으므로 주의

(실제 인게임 성공 확률과 프로그램이 인식하는 성공 확률이 다를 경우 노란색으로 추천됨)
  
7) 도달 확률이 0이면 더이상 추천하지 않음

8) 프로그램 종료시 setting.json이라는 세팅파일이 생성됨. 창 위치 및 해상도, 목표값들이 저장됨

내부 확률 계산 로직은 
https://github.com/jaentrouble/LoFAGO
로파고님의 로직을 활용하였습니다.
