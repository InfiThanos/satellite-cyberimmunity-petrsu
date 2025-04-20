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
from src.satellite_control_system.optics_control import OpticsControl
from src.satellite_control_system.command_handler import CommandHandler

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
    
    # Модуль контроля оптики (использующий монитор безопасности вместо прямых сообщений)
    optics_control = OpticsControl(
        queues_dir=queues_dir,
        log_level=LOG_DEBUG)
    
    return [sat, camera, drawer, optics_control]
    
def setup_policies():
    policies = [
        # От клиентского кода к обработчику команд
        SecurityPolicy(
                source=CLIENT_QUEUE_NAME,
                destination=COMMAND_HANDLER_QUEUE_NAME,
                operation='upload_file'
            ),
        
        # От обработчика команд к ЦСУ

        # От ЦСУ к хранилищу

        # От ЦСУ к системе управления оптикой

        # От ЦСУ к системе управления орбитой

        # От ЦСУ к системе проверки зоны

        # От хранилища к ЦСУ

        # От системы проверки зоны к ЦСУ

        # От системы управления оптикой к системе проверки зоны

        # От системы проверки зоны к камере

        # От системы проверки зоны к отрисовщику

        # От системы управления орбиты к системе проверки орбиты

        # От системы проверки орбиты к системе управления спутником
        SecurityPolicy(
                source=ORBIT_CHECK_QUEUE_NAME,
                destination=SATELITE_QUEUE_NAME,
                operation='change_orbit'
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
    
    sleep(5);
    
    system_components.stop() # Остановим системы
    system_components.clean() # Очистик систему
