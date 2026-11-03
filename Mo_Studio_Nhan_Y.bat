@echo off
chcp 65001 >nul
rem Mở Remotion Studio để chỉnh tay các chỗ nhấn ý (thư mục "sua-tay"). Studio tự lưu khi sửa;
rem chạy lại chinh_sua/nhan_y.py (cùng lệnh, thêm --cau <số câu> nếu chỉ dựng lại vài câu) để đưa chỗ đã sửa vào bản nháp.
cd /d "%~dp0remotion"
npx remotion studio src/index.jsx --port 3123
pause
