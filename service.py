from flask import Flask, render_template, request, redirect, url_for
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException
from dotenv import load_dotenv
import time, json
import os
import schedule
import threading
from datetime import datetime




app = Flask(__name__)
load_dotenv()

chrome_options = Options()
chrome_options.add_experimental_option("detach", True)
chrome_options.add_argument("--headless")  # GUI 없이 실행
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

def click_button_by_xpath(driver, xpath, log=None, data=None, key=None):
    try:
        wait = WebDriverWait(driver, 10)  # 최대 10초 대기
        wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        button = driver.find_element(By.XPATH, xpath)
        try:
            button.click()
        except:
            driver.execute_script('javascript:fncSmrtCnterResve();', button)

        if data != None:
            button.clear()
            button.send_keys(data)

        if key != None:
            button.send_keys(key)

        log_message = '[성공]' + log if log else '[성공]'
        return log_message

    except Exception as e:
        log_message = '[실패]' + log if log else f'[실패] - {e}'
        return log_message

def is_confirm_present(driver, log=None):
    try:
        time.sleep(2) 
        try:
            alert = driver.switch_to.alert
            alert.accept()
        except NoAlertPresentException:
            pass

        log_message = '[성공]' + log if log else '[성공]'
        return log_message

    except Exception as e:
        log_message = '[실패]' + log if log else f'[실패] - {e}'
        return log_message

def get_seat_code(seat):
    with open("seat_map.json", "r", encoding="utf-8") as file:
        seat_map = json.load(file)
    return seat_map.get(seat.upper(), "")


def get_user_code(user):
    with open("user_mapp.json", "r", encoding="utf-8") as file:
        user_mapp = json.load(file)
    return user_mapp.get(user, "")


def reserve_seat(driver, seat_xpath, seat):
    messages = []
    # 층수 13층으로 변경 (이 부분은 필요에 따라 사용자 입력으로 변경 가능)
    log_msg = click_button_by_xpath(driver, xpath='//*[@id="smrtcnterId"]/option[4]', log='층수 13층으로 변경')
    messages.append(log_msg)
    # 선택한 좌석 클릭
    log_msg = click_button_by_xpath(driver, xpath=seat_xpath, log=f'{seat} 번 좌석 선택')
    messages.append(log_msg)
    # 예약하기 버튼 클릭
    log_msg = click_button_by_xpath(driver, xpath='//*[@id="tooltip_reserve"]/div[1]/ul/li/a', log='예약하기 버튼 클릭')
    messages.append(log_msg)
    # alert 창 확인1
    log_msg = is_confirm_present(driver, log='Confirm 버튼 클릭')
    messages.append(log_msg)
    # alert 창 확인2
    log_msg = is_confirm_present(driver, log='Confirm 버튼 클릭')
    messages.append(log_msg)
    if '성공' in log_msg:
        messages.append(f"{seat} 좌석 예약이 완료되었습니다.")
    elif '실패' in log_msg:
        messages.append(f"{seat} 좌석 예약이 실패하였습니다.") 
    return messages

def login(driver,userid,userpw):
    messages = []
    # 로그인 창 ID 입력
    # log_msg = click_button_by_xpath(driver, xpath='//*[@id="id"]', log='로그인 창 ID 입력', data=os.environ.get('SMARTOFFICE_ID'))
    log_msg = click_button_by_xpath(driver, xpath='//*[@id="id"]', log='로그인 창 ID 입력', data=userid)
    messages.append(log_msg)
    # 로그인 창 PW 입력
    # log_msg = click_button_by_xpath(driver, xpath='//*[@id="password"]', log='로그인 창 PW 입력', data=os.environ.get('SMARTOFFICE_PW'))
    log_msg = click_button_by_xpath(driver, xpath='//*[@id="password"]', log='로그인 창 PW 입력', data=userpw)
    messages.append(log_msg)
    # 로그인 창 로그인 버튼 클릭
    log_msg = click_button_by_xpath(driver, xpath='/html/body/table/tbody/tr/td/form/div/div[2]/ul/li[3]/a', log='로그인 창 로그인 버튼 클릭')
    messages.append(log_msg)
    return messages
        


def perform_reservation(seat, user ,reserve_time_str):
    print(f"예약 작업을 시작합니다... 좌석: {seat}, 시간: {reserve_time_str}")
    driver = webdriver.Chrome(options=chrome_options)
    reservation_messages = []
    try:
        driver.get(os.environ.get('SMARTOFFICE_URL'))
        userpw = get_user_code(user)
        userid = user
        login_messages = login(driver,userid,userpw)
        reservation_messages.extend(login_messages)
        seat_code = get_seat_code(seat)
        if seat_code:
            seat_xpath = f'//*[@id="MAPSCSAT_0000000000{seat_code}"]'
            reserve_messages = reserve_seat(driver, seat_xpath, seat)
            reservation_messages.extend(reserve_messages)
            print("예약 작업이 완료되었습니다.")
        else:
            reservation_messages.append(f"좌석 '{seat}'에 대한 정보를 찾을 수 없습니다.")
            print(f"좌석 '{seat}'에 대한 정보를 찾을 수 없습니다.")
    except Exception as e:
        reservation_messages.append(f"예약 중 오류 발생: {e}")
        print(f"예약 중 오류 발생: {e}")
    finally:
        time.sleep(10)
        driver.quit()
        return reservation_messages
    
def get_current_jobs():
    jobs = []
    for job in schedule.get_jobs():
        job_kwargs = job.job_func.keywords  # 키워드 인자로 넘어간 값 가져오기
        seat = job_kwargs.get('seat', '정보없음')
        user = job_kwargs.get('user', '정보없음')
        reserve_time_str = job_kwargs.get('reserve_time_str', '정보없음')

        jobs.append({
            'user': user,
            'seat': seat,
            'reserve_time': reserve_time_str,
        })
    return jobs

def run_scheduler():
    while not stop_scheduler:
        schedule.run_pending()
        time.sleep(1)

stop_scheduler = False
scheduler_thread = None
scheduled_time = None
scheduled_seat = None
reservation_status = []
# 전역 변수에 스케줄 예약 현황 저장
scheduled_jobs = []

@app.route('/', methods=['GET', 'POST'])
def index():


    global scheduled_time
    global scheduled_seat
    global scheduled_user
    global reservation_status
    global scheduler_thread
    global scheduled_jobs
    if request.method == 'POST':
        seat = request.form['seat']
        user = request.form['user'] 
        reserve_time_str = request.form['reserve_time']
        # datetime-local에서 받은 값은 중간에 'T'가 있으므로 교체 필요
        reserve_time_str = reserve_time_str.replace('T', ' ')
        try:
            reserve_datetime = datetime.strptime(reserve_time_str, '%Y-%m-%d %H:%M')
            if reserve_datetime > datetime.now():
                schedule_time = reserve_datetime.strftime('%H:%M')
                scheduled_time = reserve_time_str
                scheduled_seat = seat
                scheduled_user = user

                schedule.every().day.at(schedule_time).do(schedule_reservation_job, seat=scheduled_seat, user=scheduled_user , reserve_time_str=scheduled_time)

                if scheduler_thread is None or not scheduler_thread.is_alive():
                    global stop_scheduler
                    stop_scheduler = False
                    scheduler_thread = threading.Thread(target=run_scheduler)
                    scheduler_thread.daemon = True
                    scheduler_thread.start()

                return render_template('index.html', message=f"'{user}'가 '{seat}' 좌석이 {reserve_time_str}에 예약되도록 스케줄되었습니다.", 
                                       alerts=reservation_status)
            else:
                return render_template('index.html', error="예약 시간은 현재 시간 이후로 설정해야 합니다.",
                                        alerts=reservation_status,
                                        scheduled_jobs=get_current_jobs())
        except ValueError:
            return render_template('index.html', error="잘못된 시간 형식입니다.YYYY-MM-DD HH:MM 형식으로 입력해주세요.",
                                    alerts=reservation_status,
                                    scheduled_jobs=get_current_jobs())
    return render_template('index.html',alerts=reservation_status,
                           scheduled_jobs=get_current_jobs())
@app.route('/seat_info')
def seat_info():
    import json
    with open("seat_map.json", "r", encoding="utf-8") as file:
        seat_map = json.load(file)
    with open("user_mapp.json", "r", encoding="utf-8") as file:
        user_map = json.load(file)

    user_keys = list(user_map.keys())
    seat_keys = list(seat_map.keys())

    return render_template('seat_info.html', seat_keys=seat_keys, user_keys=user_keys)

@app.route('/cancel_all_reservations')
def cancel_all_reservations():
    schedule.clear()  # 모든 예약 제거
    return redirect(url_for('index'))


def schedule_reservation_job(seat,user, reserve_time_str):
    global reservation_status
    reservation_status = perform_reservation(seat, user , reserve_time_str)

@app.route('/shutdown_scheduler')
def shutdown_scheduler():
    global stop_scheduler
    stop_scheduler = True
    if scheduler_thread and scheduler_thread.is_alive():
        scheduler_thread.join()
    return "스케줄러가 종료되었습니다."

if __name__ == '__main__':
    app.run(debug=True)
