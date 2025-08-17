import React, { useEffect, useRef, useState } from 'react';
import { MapPin, Navigation, Clock, Calculator, AlertCircle } from 'lucide-react';

const RouteMap = ({ fromAddress, toAddress, warehouseName, onRouteCalculated }) => {
  const mapRef = useRef(null);
  const [map, setMap] = useState(null);
  const [route, setRoute] = useState(null);
  const [distance, setDistance] = useState('');
  const [duration, setDuration] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [mapReady, setMapReady] = useState(false);
  const [initStatus, setInitStatus] = useState('Начинаем инициализацию...');
  const mountedRef = useRef(true); // Отслеживаем mounted состояние

  // Cleanup при размонтировании - ИСПРАВЛЕНИЕ для removeChild ошибки
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      console.log('🧹 Cleanup RouteMap component');
      
      // Добавляем задержку для безопасной очистки
      setTimeout(() => {
        try {
          // Очищаем карту перед размонтированием
          if (map) {
            try {
              // Сначала удаляем все geoObjects если есть
              if (map.geoObjects) {
                map.geoObjects.removeAll();
              }
              map.destroy();
            } catch (e) {
              console.warn('Предупреждение при destroy карты:', e);
            }
          }
          
          // Безопасная очистка mapRef
          if (mapRef.current && mapRef.current.parentNode) {
            try {
              mapRef.current.innerHTML = '';
            } catch (e) {
              console.warn('Предупреждение при очистке контейнера:', e);
            }
          }
        } catch (error) {
          console.warn('Предупреждение при cleanup RouteMap:', error);
        }
      }, 0);
    };
  }, [map]);

  // Инициализация карты
  useEffect(() => {
    if (!mapRef.current || map || mapReady || !mountedRef.current) return;

    const initMap = async () => {
      try {
        if (!mountedRef.current) return;
        
        console.log('🗺️ Начинаем инициализацию карты...');
        setInitStatus('Проверяем API ключ...');
        
        const apiKey = process.env.REACT_APP_YANDEX_MAPS_API_KEY;
        console.log('🔑 API ключ:', apiKey ? 'найден' : 'НЕ НАЙДЕН');
        
        if (!apiKey) {
          throw new Error('API ключ Yandex Maps не найден');
        }

        if (!mountedRef.current) return;
        setInitStatus('Загружаем Yandex Maps API...');

        // Простая загрузка скрипта
        if (!window.ymaps) {
          console.log('📡 Загружаем скрипт Yandex Maps...');
          
          const script = document.createElement('script');
          script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
          script.async = true;
          
          const scriptPromise = new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
              reject(new Error('Таймаут загрузки скрипта (20 сек)'));
            }, 20000);
            
            script.onload = () => {
              clearTimeout(timeout);
              console.log('✅ Скрипт Yandex Maps загружен');
              resolve();
            };
            script.onerror = () => {
              clearTimeout(timeout);
              reject(new Error('Не удалось загрузить Yandex Maps API'));
            };
          });
          
          document.head.appendChild(script);
          await scriptPromise;
        }

        if (!mountedRef.current) return;
        setInitStatus('Ожидаем готовности API...');

        // Ждем готовности API
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('Таймаут готовности API (15 сек)'));
          }, 15000);

          if (window.ymaps) {
            window.ymaps.ready(() => {
              clearTimeout(timeout);
              console.log('✅ Yandex Maps API готов');
              resolve();
            });
          } else {
            clearTimeout(timeout);
            reject(new Error('window.ymaps недоступен'));
          }
        });

        if (!mountedRef.current) return;
        setInitStatus('Создаем карту...');

        // Проверяем что контейнер еще существует
        if (!mapRef.current) {
          throw new Error('Контейнер карты недоступен');
        }

        // Создаем карту
        const ymaps = window.ymaps;
        console.log('🗺️ Создаем карту в контейнере');
        
        const newMap = new ymaps.Map(mapRef.current, {
          center: [55.7558, 37.6173], // Москва
          zoom: 10,
          controls: ['zoomControl', 'fullscreenControl']
        });

        if (!mountedRef.current) {
          // Если компонент размонтирован, уничтожаем карту
          newMap.destroy();
          return;
        }

        console.log('✅ Карта создана успешно');
        setMap(newMap);
        setMapReady(true);
        setInitStatus('Карта готова!');

      } catch (error) {
        if (!mountedRef.current) return;
        
        console.error('❌ Ошибка инициализации карты:', error);
        setError(`Ошибка загрузки карты: ${error.message}`);
        setInitStatus(`Ошибка: ${error.message}`);
      }
    };

    initMap();
  }, [map, mapReady]);

  // Построение маршрута
  useEffect(() => {
    if (!map || !fromAddress || !toAddress || !mapReady || !mountedRef.current) {
      return;
    }

    const buildRoute = async () => {
      if (!mountedRef.current) return;
      
      setLoading(true);
      setError('');
      setDistance('');
      setDuration('');

      try {
        const ymaps = window.ymaps;
        if (!ymaps || !mountedRef.current) return;

        // Очищаем карту
        map.geoObjects.removeAll();

        console.log(`🗺️ Строим маршрут от "${fromAddress}" до "${toAddress}"`);

        // Создаем маршрут
        const multiRoute = new ymaps.multiRouter.MultiRoute({
          referencePoints: [fromAddress, toAddress],
          params: {
            routingMode: 'auto',
            avoidTrafficJams: false
          }
        }, {
          boundsAutoApply: true,
          routeActiveStrokeWidth: 4,
          routeActiveStrokeColor: '#3B82F6',
          wayPointDraggable: false
        });

        if (!mountedRef.current) return;

        map.geoObjects.add(multiRoute);
        setRoute(multiRoute);

        // Обработчик успеха
        multiRoute.model.events.add('requestsuccess', () => {
          if (!mountedRef.current) return;
          
          try {
            console.log('✅ Маршрут построен');
            const activeRoute = multiRoute.getActiveRoute();
            
            if (activeRoute && mountedRef.current) {
              const distanceValue = activeRoute.properties.get('distance');
              const durationObj = activeRoute.properties.get('duration');

              // Форматирование данных
              let distanceText = 'Неизвестно';
              if (typeof distanceValue === 'number' && !isNaN(distanceValue) && distanceValue > 0) {
                distanceText = distanceValue >= 1000 
                  ? `${(distanceValue / 1000).toFixed(1)} км`
                  : `${Math.round(distanceValue)} м`;
              }

              let durationText = 'Неизвестно';
              let durationValue = 0;
              
              if (durationObj && typeof durationObj.value === 'number') {
                durationValue = durationObj.value;
                const totalMinutes = Math.round(durationValue / 60);
                const hours = Math.floor(totalMinutes / 60);
                const minutes = totalMinutes % 60;
                durationText = hours > 0 
                  ? `${hours} ч ${minutes} мин`
                  : `${minutes} мин`;
              }

              if (mountedRef.current) {
                setDistance(distanceText);
                setDuration(durationText);

                if (onRouteCalculated) {
                  onRouteCalculated({
                    distance: distanceText,
                    duration: durationText,
                    distanceValue: distanceValue || 0,
                    durationValue: durationValue
                  });
                }

                console.log(`✅ Результат: ${distanceText}, время: ${durationText}`);
              }

              // Добавляем маркеры
              if (mountedRef.current) {
                try {
                  const routeCoords = activeRoute.geometry.getCoordinates();
                  if (routeCoords && routeCoords.length > 0) {
                    const startCoord = routeCoords[0];
                    const endCoord = routeCoords[routeCoords.length - 1];

                    const startPlacemark = new ymaps.Placemark(startCoord, {
                      balloonContent: `<strong>Адрес забора:</strong><br/>${fromAddress}`,
                      iconContent: 'А'
                    }, {
                      preset: 'islands#redStretchyIcon'
                    });

                    const endPlacemark = new ymaps.Placemark(endCoord, {
                      balloonContent: `<strong>Склад:</strong><br/>${toAddress}`,
                      iconContent: 'Б'
                    }, {
                      preset: 'islands#greenStretchyIcon'
                    });

                    if (mountedRef.current && map) {
                      map.geoObjects.add(startPlacemark);
                      map.geoObjects.add(endPlacemark);
                      console.log('✅ Маркеры добавлены');
                    }
                  }
                } catch (markerError) {
                  console.error('⚠️ Ошибка маркеров:', markerError);
                }
              }
            }
          } catch (routeError) {
            if (mountedRef.current) {
              console.error('❌ Ошибка обработки маршрута:', routeError);
              setError('Ошибка обработки данных маршрута');
            }
          }
        });

        // Обработчик ошибок
        multiRoute.model.events.add('requestfail', (e) => {
          if (mountedRef.current) {
            console.error('❌ Ошибка построения маршрута:', e);
            setError('Не удалось построить маршрут. Проверьте адреса.');
          }
        });

      } catch (error) {
        if (mountedRef.current) {
          console.error('❌ Ошибка при построении маршрута:', error);
          setError(`Ошибка: ${error.message}`);
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    };

    const debounceTimer = setTimeout(buildRoute, 1500);
    return () => clearTimeout(debounceTimer);
  }, [map, fromAddress, toAddress, mapReady]);

  // Показываем состояние загрузки карты
  if (!mapReady && !error) {
    return (
      <div className="space-y-3">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center justify-center mb-2">
            <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-600 border-t-transparent mr-3"></div>
            <span className="text-blue-700 font-medium">Загрузка карты...</span>
          </div>
          <div className="text-center text-sm text-blue-600">
            {initStatus}
          </div>
          <div className="mt-3 text-xs text-gray-500 text-center">
            🔧 Откройте консоль браузера (F12) для подробной отладки
          </div>
        </div>
        <div className="border border-gray-300 rounded-lg bg-gray-100 h-64 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="animate-pulse mb-2">🗺️</div>
            <div>Инициализация карты</div>
            <div className="text-xs mt-1">{initStatus}</div>
          </div>
        </div>
      </div>
    );
  }

  // Показываем ошибку
  if (error && !mapReady) {
    return (
      <div className="space-y-3">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center mb-2">
            <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
            <span className="text-red-700 font-medium">Ошибка загрузки карты</span>
          </div>
          <p className="text-red-600 text-sm mb-3">{error}</p>
          <div className="text-xs text-gray-600 mb-3">
            Статус: {initStatus}
          </div>
          <button 
            onClick={() => window.location.reload()} 
            className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
          >
            Перезагрузить страницу
          </button>
        </div>
        <div className="border border-red-300 rounded-lg bg-red-50 h-64 flex items-center justify-center">
          <div className="text-center text-red-600">
            <AlertCircle className="h-8 w-8 mx-auto mb-2" />
            <div>Карта недоступна</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Информация о маршруте */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
        <div className="flex items-center mb-2">
          <Navigation className="h-4 w-4 text-blue-600 mr-2" />
          <span className="font-medium text-blue-900">Маршрут доставки</span>
        </div>
        
        <div className="space-y-2 text-sm">
          <div className="flex items-start">
            <div className="bg-red-100 text-red-700 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-2 mt-0.5 flex-shrink-0">
              А
            </div>
            <div>
              <span className="font-medium text-red-800">Адрес забора:</span>
              <p className="text-gray-700">{fromAddress}</p>
            </div>
          </div>
          
          <div className="flex items-start">
            <div className="bg-green-100 text-green-700 rounded-full w-6 h-6 flex items-center justify-center text-xs font-bold mr-2 mt-0.5 flex-shrink-0">
              Б
            </div>
            <div>
              <span className="font-medium text-green-800">{warehouseName}:</span>
              <p className="text-gray-700">{toAddress}</p>
            </div>
          </div>
        </div>

        {loading && (
          <div className="flex items-center mt-3 text-blue-600">
            <div className="animate-spin rounded-full h-4 w-4 border-2 border-blue-600 border-t-transparent mr-2"></div>
            <span className="text-sm">Построение маршрута...</span>
          </div>
        )}

        {error && mapReady && (
          <div className="mt-3 text-red-600 text-sm">
            <AlertCircle className="h-4 w-4 inline mr-1" />
            {error}
          </div>
        )}

        {distance && duration && !loading && !error && (
          <div className="flex items-center justify-between mt-3 pt-3 border-t border-blue-200">
            <div className="flex items-center text-blue-700">
              <Calculator className="h-4 w-4 mr-1" />
              <span className="font-medium">{distance}</span>
            </div>
            <div className="flex items-center text-blue-700">
              <Clock className="h-4 w-4 mr-1" />
              <span className="font-medium">{duration}</span>
            </div>
          </div>
        )}
      </div>

      {/* Карта */}
      <div className="border border-gray-300 rounded-lg overflow-hidden">
        <div
          ref={mapRef}
          style={{ width: '100%', height: '300px' }}
          className="bg-gray-100"
        />
      </div>
    </div>
  );
};

export default RouteMap;