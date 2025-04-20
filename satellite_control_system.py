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
from src.satellite_control_system.interpreter import Interpreter
from src.satellite_control_system.authorization_center import AuthorizationCenter

from src.system.config import CRITICALITY_STR, LOG_DEBUG, \
    LOG_ERROR, LOG_INFO, DEFAULT_LOG_LEVEL, OPTICS_CONTROL_QUEUE_NAME, ORBIT_DRAWER_QUEUE_NAME,\
    INTERPRETER_QUEUE_NAME, AUTHORIZATION_CENTER_QUEUE_NAME
    
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
        SecurityPolicy(
                source=INTERPRETER_QUEUE_NAME,
                destination=AUTHORIZATION_CENTER_QUEUE_NAME,
                operation='execute commands'
            )]
            
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
