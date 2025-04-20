import numpy as np

from time import sleep
from multiprocessing import Queue

from src.satellite_simulator.satellite import Satellite
from src.satellite_simulator.orbit_drawer import OrbitDrawer
from src.satellite_simulator.camera import Camera
from src.system.queues_dir import QueuesDirectory
from src.system.system_wrapper import SystemComponentsContainer
from src.system.event_types import Event, ControlEvent
from src.satellite_control_system.security_monitor import SecurityMonitor
from src.system.security_policy_type import SecurityPolicy

from src.satellite_control_system.client import Client
from src.satellite_control_system.command_handler import CommandHandler
from src.satellite_control_system.csu import CentralControlSystem
from src.satellite_control_system.database import DataBase
from src.satellite_control_system.optics_check import OpticsCheck
from src.satellite_control_system.optics_control import OpticsControl
from src.satellite_control_system.orbit_check import OrbitCheck
from src.satellite_control_system.orbit_control import OrbitControl


from src.system.config import CRITICALITY_STR, LOG_DEBUG, \
    LOG_ERROR, LOG_INFO, DEFAULT_LOG_LEVEL, \
    SATELITE_QUEUE_NAME, \
    ORBIT_DRAWER_QUEUE_NAME, \
    OPTICS_CONTROL_QUEUE_NAME, \
    ZONE_CHECK_QUEUE_NAME, \
    ORBIT_CONTROL_QUEUE_NAME, \
    ORBIT_CHECK_QUEUE_NAME, \
    CAMERA_QUEUE_NAME, \
    SECURITY_MONITOR_QUEUE_NAME, \
    CLIENT_QUEUE_NAME, \
    CENTRAL_CONTROL_SYSTEM_QUEUE_NAME, \
    DATA_STORAGE_QUEUE_NAME, \
    COMMAND_HANDLER_QUEUE_NAME
    
def setup_system(queues_dir):
    # Симулятор спутника
    sat = Satellite(
        altitude=1000e3,
        position_angle=0,
        inclination=np.pi/3,
        raan=0,
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Симулятор камеры спутника
    camera = Camera(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Отрисовщик
    drawer = OrbitDrawer(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Клиент
    client = Client(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Обработчик команд
    command_handler = CommandHandler(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # ЦСУ
    csu = CentralControlSystem(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Хранилище
    db = DataBase(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Проверка запретных зон
    optic_checker = OpticsCheck(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Модуль контроля оптики
    optics_control = OpticsControl(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Проверка значений орбиты
    orbit_checker = OrbitCheck(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)

    # Модуль контроля орбиты
    orbit_control = OrbitControl(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)
    
    return [sat, camera, drawer, client, command_handler, csu, db,
            optic_checker, optics_control, orbit_checker, orbit_control]
    
def setup_policies():
    policies = [
        # От клиентского кода к обработчику команд
        SecurityPolicy(
                source=CLIENT_QUEUE_NAME,
                destination=COMMAND_HANDLER_QUEUE_NAME,
                operation='upload_file'
            ),
        
        # От обработчика команд к ЦСУ
        SecurityPolicy(
                source=COMMAND_HANDLER_QUEUE_NAME,
                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                operation='ORBIT'
            ),
        SecurityPolicy(
                source=COMMAND_HANDLER_QUEUE_NAME,
                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                operation='ADD ZONE'
            ),
        SecurityPolicy(
                source=COMMAND_HANDLER_QUEUE_NAME,
                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                operation='REMOVE ZONE'
            ),
        SecurityPolicy(
                source=COMMAND_HANDLER_QUEUE_NAME,
                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                operation='MAKE PHOTO'
            ),

        # От ЦСУ к хранилищу
        SecurityPolicy(
                source=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                destination=DATA_STORAGE_QUEUE_NAME,
                operation='add_zone'
            ),
        SecurityPolicy(
                source=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                destination=DATA_STORAGE_QUEUE_NAME,
                operation='delete_zone'
            ),
        SecurityPolicy(
                source=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                destination=DATA_STORAGE_QUEUE_NAME,
                operation='request_zone'
            ),
        SecurityPolicy(
                source=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                destination=DATA_STORAGE_QUEUE_NAME,
                operation='add_photo'
            ),
        
        # От ЦСУ к системе управления оптикой
        SecurityPolicy(
                source=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                destination=OPTICS_CONTROL_QUEUE_NAME,
                operation='request_photo'
            ),
        
        # От ЦСУ к системе управления орбитой
        SecurityPolicy(
                source=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                destination=ORBIT_CONTROL_QUEUE_NAME,
                operation='change_orbite'
            ),

        # От ЦСУ к системе проверки зоны
        SecurityPolicy(
                source=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                destination=ZONE_CHECK_QUEUE_NAME,
                operation='post_photo'
            ),

        # От хранилища к ЦСУ
        SecurityPolicy(
                source=DATA_STORAGE_QUEUE_NAME,
                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                operation='update_photo'
            ),
        
        # От системы управления оптикой к системе проверки зоны
        SecurityPolicy(
            source=OPTICS_CONTROL_QUEUE_NAME,
            destination=ZONE_CHECK_QUEUE_NAME,
            operation='request_зрщещ'
        ),

        # От системы проверки зоны к ЦСУ
        SecurityPolicy(
                source=ZONE_CHECK_QUEUE_NAME,
                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                operation='request_zone'
            ),
        SecurityPolicy(
                source=ZONE_CHECK_QUEUE_NAME,
                destination=CENTRAL_CONTROL_SYSTEM_QUEUE_NAME,
                operation='add_photo'
            ),

        # От системы проверки зоны к камере
        SecurityPolicy(
                source=ZONE_CHECK_QUEUE_NAME,
                destination=CAMERA_QUEUE_NAME,
                operation='request_photo'
            ),
        
        # От системы проверки зоны к отрисовщику
        SecurityPolicy(
                source=ZONE_CHECK_QUEUE_NAME,
                destination=ORBIT_DRAWER_QUEUE_NAME,
                operation='update_photo'
            ),
        
        # От системы управления орбиты к системе проверки орбиты
        SecurityPolicy(
                source=ORBIT_CONTROL_QUEUE_NAME,
                destination=ORBIT_CHECK_QUEUE_NAME,
                operation='check_orbit'
            ),

        # От системы проверки орбиты к системе управления спутником
        SecurityPolicy(
                source=ORBIT_CHECK_QUEUE_NAME,
                destination=SATELITE_QUEUE_NAME,
                operation='change_orbit'
            ),

        # От камеры к системе проверки зоны
        SecurityPolicy(
                source=ORBIT_CHECK_QUEUE_NAME,
                destination=ZONE_CHECK_QUEUE_NAME,
                operation='check_photo'
            )
        ]
            
    return policies

if __name__ == '__main__':
    queues_dir = QueuesDirectory()

    security_monitor = SecurityMonitor(queues_dir=queues_dir, log_level=LOG_DEBUG, policies=setup_policies())
    
    # Создадим модули системы
    modules = setup_system(queues_dir)
    modules.append(security_monitor)

    system_components = SystemComponentsContainer(
        components=modules,
        log_level=LOG_DEBUG)
    
    # Запустим систему 
    system_components.start()
    
    sleep(20)
    
    system_components.stop() # Остановим системы
    system_components.clean() # Очистим систему
