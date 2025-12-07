"""
Clase base abstracta para fuentes de datos meteorológicos.

Este módulo define la interfaz común que deben implementar todas
las fuentes de datos meteorológicos, incluyendo manejo de errores,
sistema de reintentos con backoff exponencial, y logging.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import time
import logging
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)


class BaseWeatherSource(ABC):
    """
    Clase base abstracta para todas las fuentes de datos meteorológicos.

    Esta clase proporciona funcionalidad común como manejo de errores,
    reintentos automáticos, y logging. Las clases hijas deben implementar
    los métodos abstractos para obtener datos específicos de cada API.
    """

    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
    ):
        """
        Inicializa la fuente de datos.

        Args:
            name: Nombre de la fuente de datos
            base_url: URL base de la API
            api_key: API key (opcional, depende de la fuente)
            timeout: Timeout de peticiones HTTP en segundos
            max_retries: Número máximo de reintentos
            retry_backoff_factor: Factor de backoff exponencial
        """
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor

        # Configurar sesión HTTP con reintentos
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=retry_backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        logger.info(f"Fuente de datos '{name}' inicializada")

    @abstractmethod
    def get_current_weather(
        self, latitude: float, longitude: float, **kwargs
    ) -> Dict[str, Any]:
        """
        Obtiene el clima actual para una ubicación.

        Args:
            latitude: Latitud de la ubicación
            longitude: Longitud de la ubicación
            **kwargs: Argumentos adicionales específicos de la fuente

        Returns:
            Dict[str, Any]: Diccionario con los datos del clima actual

        Raises:
            NotImplementedError: Si no está implementado en la subclase
        """
        raise NotImplementedError(
            "Las subclases deben implementar get_current_weather()"
        )

    @abstractmethod
    def get_forecast(
        self,
        latitude: float,
        longitude: float,
        days: int = 5,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Obtiene el pronóstico del clima para una ubicación.

        Args:
            latitude: Latitud de la ubicación
            longitude: Longitud de la ubicación
            days: Número de días de pronóstico
            **kwargs: Argumentos adicionales específicos de la fuente

        Returns:
            Dict[str, Any]: Diccionario con los datos del pronóstico

        Raises:
            NotImplementedError: Si no está implementado en la subclase
        """
        raise NotImplementedError(
            "Las subclases deben implementar get_forecast()"
        )

    def _make_request(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET",
        **kwargs,
    ) -> requests.Response:
        """
        Realiza una petición HTTP con manejo de errores y reintentos.

        Args:
            endpoint: Endpoint de la API (se concatena con base_url)
            params: Parámetros de la petición
            method: Método HTTP (GET o POST)
            **kwargs: Argumentos adicionales para requests

        Returns:
            requests.Response: Respuesta de la petición

        Raises:
            requests.exceptions.RequestException: Si la petición falla
            ValueError: Si los parámetros son inválidos
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Agregar API key si está disponible
        if self.api_key and params is not None:
            params = params.copy()
            if "appid" not in params and "key" not in params:
                params["key"] = self.api_key

        logger.debug(f"Realizando petición {method} a {url} con params: {params}")

        try:
            if method.upper() == "GET":
                response = self.session.get(
                    url, params=params, timeout=self.timeout, **kwargs
                )
            elif method.upper() == "POST":
                response = self.session.post(
                    url, json=params, timeout=self.timeout, **kwargs
                )
            else:
                raise ValueError(f"Método HTTP no soportado: {method}")

            response.raise_for_status()
            logger.debug(
                f"Petición exitosa: {response.status_code} - "
                f"{len(response.content)} bytes"
            )
            return response

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout al conectar con {self.name}: {e}")
            raise
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Error HTTP {e.response.status_code} de {self.name}: {e}"
            )
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al conectar con {self.name}: {e}")
            raise

    def _retry_with_backoff(
        self, func, *args, max_attempts: Optional[int] = None, **kwargs
    ):
        """
        Ejecuta una función con reintentos y backoff exponencial.

        Args:
            func: Función a ejecutar
            *args: Argumentos posicionales para la función
            max_attempts: Número máximo de intentos (usa self.max_retries si None)
            **kwargs: Argumentos nombrados para la función

        Returns:
            Resultado de la función

        Raises:
            Exception: Si todos los intentos fallan
        """
        if max_attempts is None:
            max_attempts = self.max_retries

        last_exception = None
        for attempt in range(max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < max_attempts - 1:
                    wait_time = self.retry_backoff_factor ** attempt
                    logger.warning(
                        f"Intento {attempt + 1}/{max_attempts} falló. "
                        f"Reintentando en {wait_time:.2f}s... Error: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Todos los intentos fallaron después de "
                        f"{max_attempts} intentos"
                    )

        raise last_exception

    def is_available(self) -> bool:
        """
        Verifica si la fuente de datos está disponible.

        Returns:
            bool: True si la fuente está disponible, False en caso contrario
        """
        try:
            # Intentar una petición simple
            response = self._make_request("", params={})
            return response.status_code < 500
        except Exception as e:
            logger.warning(f"Fuente {self.name} no disponible: {e}")
            return False

    def __repr__(self) -> str:
        """Representación en string de la instancia."""
        return f"{self.__class__.__name__}(name='{self.name}')"

