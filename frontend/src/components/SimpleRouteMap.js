import React, { useEffect, useRef, useState } from 'react';
import { Navigation, AlertCircle } from 'lucide-react';

const SimpleRouteMap = ({ fromAddress, toAddress, warehouseName }) => {
  const mapRef = useRef(null);
  const [map, setMap] = useState(null);
  const [status, setStatus] = useState('Инициализация...');
  const [error, setError] = useState('');
  const mountedRef = useRef(true); // Отслеживаем mounted состояние

  // Cleanup при размонтировании - ИСПРАВЛЕНИЕ для removeChild ошибки
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      console.log('🧹 Cleanup SimpleRouteMap component');
      
      // Добавляем задержку для безопасной очистки
      setTimeout(() => {
        try {
          // Уничтожаем карту перед размонтированием
          if (map) {
            try {
              // Сначала удаляем все geoObjects если есть
              if (map.geoObjects) {
                map.geoObjects.removeAll();
              }
              map.destroy();
            } catch (e) {
              console.warn('Предупреждение при destroy карты в SimpleRouteMap:', e);
            }
          }
          
          // Безопасная очистка контейнера только после уничтожения карты
          if (mapRef.current && mapRef.current.parentNode) {
            try {
              mapRef.current.innerHTML = '';
            } catch (e) {
              console.warn('Предупреждение при очистке контейнера в SimpleRouteMap:', e);
            }
          }
        } catch (error) {
          console.warn('Предупреждение при cleanup SimpleRouteMap:', error);
        }
      }, 0);
    };
  }, [map]);

  useEffect(() => {
    const initSimpleMap = async () => {
      try {
        if (!mountedRef.current) return;
        
        setStatus('Проверяем API ключ...');
        
        const apiKey = process.env.REACT_APP_YANDEX_MAPS_API_KEY;
        console.log('🔑 SimpleMap API ключ:', apiKey ? `${apiKey.substring(0, 8)}...` : 'НЕ НАЙДЕН');
        
        if (!apiKey) {
          throw new Error('API ключ Yandex Maps не найден в переменных окружения');
        }

        if (!mountedRef.current) return;
        setStatus('Загружаем скрипт...');
        
        // Проверяем доступность Yandex Maps
        const testUrl = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
        console.log('🌐 SimpleMap URL скрипта:', testUrl);

        // Простая загрузка скрипта если еще не загружен
        if (!window.ymaps) {
          const script = document.createElement('script');
          script.src = testUrl;
          script.async = true;
          
          const loadPromise = new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
              reject(new Error('Таймаут загрузки скрипта (20 сек)'));
            }, 20000);
            
            script.onload = () => {
              clearTimeout(timeout);
              resolve();
            };
            script.onerror = () => {
              clearTimeout(timeout);
              reject(new Error('Скрипт не загружается'));
            };
          });
          
          document.head.appendChild(script);
          await loadPromise;
        }
        
        if (!mountedRef.current) return;
        setStatus('Скрипт загружен, ждем API...');
        console.log('✅ SimpleMap скрипт загружен, window.ymaps:', !!window.ymaps);

        // Ждем готовности API
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('API не готов в течение 10 секунд'));
          }, 10000);
          
          if (window.ymaps) {
            window.ymaps.ready(() => {
              clearTimeout(timeout);
              console.log('✅ SimpleMap Yandex Maps API готов');
              resolve();
            });
          } else {
            clearTimeout(timeout);
            reject(new Error('window.ymaps недоступен после загрузки скрипта'));
          }
        });

        if (!mountedRef.current || !mapRef.current) return;
        setStatus('Создаем карту...');
        
        // Создаем карту
        const ymaps = window.ymaps;
        const newMap = new ymaps.Map(mapRef.current, {
          center: [55.7558, 37.6173], // Москва
          zoom: 10,
          controls: []
        });

        if (!mountedRef.current) {
          // Если размонтирован, уничтожаем карту
          newMap.destroy();
          return;
        }

        setMap(newMap);
        setStatus('✅ Карта создана успешно!');
        console.log('✅ SimpleMap карта создана');

        // Если есть адреса, добавляем маркеры
        if (fromAddress && toAddress && mountedRef.current) {
          setStatus('Добавляем маркеры...');
          
          try {
            // Геокодируем адреса
            const geocoder = ymaps.geocode(fromAddress);
            geocoder.then((res) => {
              if (!mountedRef.current || !newMap) return;
              
              const firstGeoObject = res.geoObjects.get(0);
              if (firstGeoObject) {
                const coords = firstGeoObject.geometry.getCoordinates();
                
                const placemark = new ymaps.Placemark(coords, {
                  balloonContent: `Адрес забора: ${fromAddress}`
                }, {
                  preset: 'islands#redIcon'
                });
                
                if (mountedRef.current && newMap) {
                  newMap.geoObjects.add(placemark);
                  setStatus('✅ Карта готова с маркерами!');
                }
              }
            }).catch((error) => {
              if (!mountedRef.current) return;
              console.error('Ошибка геокодирования:', error);
              setStatus('⚠️ Карта создана, но без маркеров');
            });
          } catch (geocodeError) {
            console.error('Ошибка при добавлении маркеров:', geocodeError);
            setStatus('⚠️ Карта создана, но без маркеров');
          }
        }

      } catch (error) {
        if (!mountedRef.current) return;
        
        console.error('❌ Ошибка простой карты:', error);
        setError(`Ошибка: ${error.message}`);
        setStatus(`❌ ${error.message}`);
      }
    };

    if (mapRef.current && mountedRef.current) {
      initSimpleMap();
    }
  }, [fromAddress, toAddress]);

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center mb-2">
          <AlertCircle className="h-5 w-5 text-red-500 mr-2" />
          <span className="text-red-700 font-medium">Простая карта: Ошибка</span>
        </div>
        <p className="text-red-600 text-sm">{error}</p>
        <div className="text-xs text-gray-600 mt-2">
          Статус: {status}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
        <div className="flex items-center mb-2">
          <Navigation className="h-4 w-4 text-green-600 mr-2" />
          <span className="font-medium text-green-900">Простая тестовая карта</span>
        </div>
        <div className="text-sm text-green-700">
          Статус: {status}
        </div>
        {fromAddress && toAddress && (
          <div className="text-xs text-gray-600 mt-2">
            От: {fromAddress} → До: {toAddress}
          </div>
        )}
      </div>
      
      <div className="border border-gray-300 rounded-lg overflow-hidden">
        <div
          ref={mapRef}
          style={{ width: '100%', height: '250px' }}
          className="bg-gray-100"
        />
      </div>
    </div>
  );
};

export default SimpleRouteMap;