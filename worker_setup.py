from selenium import webdriver


class Browser:
    
    def __init__(self, geckodriver_path):
        geckodriver_path = r'C:\Users\nicol\anaconda3\Library\bin\geckodriver'
        self.driver = webdriver.Firefox(executable_path=geckodriver_path)

        
def dask_setup(worker):
    geckodriver_path = r'C:\Users\nicol\anaconda3\Library\bin\geckodriver'
    worker.browser = Browser(geckodriver_path)

    # Código para acceder al número de threads por worker:
    # print([worker['nthreads'] for worker in client.scheduler_info()['workers'].values()])