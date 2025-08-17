import React, { useEffect, useRef, useState } from 'react';
import { MapPin } from 'lucide-react';

const SingleAddressMap = ({ address, title = "Адрес получения груза" }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const mountedRef = useRef(true);
  
  const [mapReady, setMapReady] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [initStatus, setInitStatus] = useState('Инициализация...');

  // Cleanup при размонтировании - ИСПРАВЛЕНИЕ для removeChild ошибки
  useEffect(() => {
    return () => {
      mountedRef.current = false;
      console.log('🧹 Cleanup SingleAddressMap component');
      
      // Добавляем задержку для безопасной очистки
      setTimeout(() => {
        try {
          if (mapInstanceRef.current) {
            // Сначала удаляем все geoObjects если есть
            if (mapInstanceRef.current.geoObjects) {
              mapInstanceRef.current.geoObjects.removeAll();
            }
            mapInstanceRef.current.destroy();
            mapInstanceRef.current = null;
          }
          
          // Безопасная очистка контейнера только после уничтожения карты
          if (mapRef.current && mapRef.current.parentNode) {
            try {
              mapRef.current.innerHTML = '';
            } catch (e) {
              console.warn('Предупреждение при очистке контейнера в SingleAddressMap:', e);
            }
          }
        } catch (error) {
          console.warn('Предупреждение при cleanup SingleAddressMap:', error);
        }
      }, 0);
    };
  }, []);

  // Инициализация карты
  useEffect(() => {
    if (mapInstanceRef.current || !mountedRef.current) return;

    const initMap = async () => {
      try {
        setInitStatus('Загружаем Yandex Maps API...');
        
        // Получаем API ключ
        const apiKey = process.env.REACT_APP_YANDEX_MAPS_API_KEY;
        console.log('🔑 SingleAddressMap API ключ:', apiKey ? 'найден' : 'НЕ НАЙДЕН');

        // Проверяем, загружен ли уже скрипт
        if (!window.ymaps) {
          setInitStatus('Загружаем скрипт Yandex Maps...');
          console.log('📦 Загружаем новый скрипт Yandex Maps для SingleAddressMap');
          
          const existingScript = document.querySelector('script[src*="api-maps.yandex.ru"]');
          if (existingScript) {
            console.log('📦 Скрипт Yandex Maps уже существует, ждем загрузки...');
            // Ждем пока загрузится существующий скрипт
            let attempts = 0;
            while (!window.ymaps && attempts < 50) {
              await new Promise(resolve => setTimeout(resolve, 100));
              attempts++;
            }
            if (!window.ymaps) {
              throw new Error('Скрипт Yandex Maps не загрузился за отведенное время');
            }
          } else {
            const script = document.createElement('script');
            script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
            script.async = true;

            const scriptPromise = new Promise((resolve, reject) => {
              script.onload = () => {
                console.log('✅ Скрипт Yandex Maps загружен успешно');
                resolve();
              };
              script.onerror = (error) => {
                console.error('❌ Ошибка загрузки скрипта Yandex Maps:', error);
                reject(error);
              };
            });

            document.head.appendChild(script);
            await scriptPromise;
          }
        } else {
          console.log('✅ Yandex Maps API уже доступен');
        }

        if (!mountedRef.current) return;

        // Ждем готовности API
        setInitStatus('Инициализация карты...');
        console.log('🗺️ Инициализируем Yandex Maps API...');
        
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => {
            reject(new Error('Timeout при инициализации Yandex Maps'));
          }, 10000);
          
          window.ymaps.ready(() => {
            clearTimeout(timeout);
            console.log('✅ Yandex Maps API готов');
            resolve();
          });
        });

        if (!mountedRef.current) return;

        // Создаем карту
        setInitStatus('Создание экземпляра карты...');
        console.log('🗺️ Создаем новую карту SingleAddressMap...');
        
        if (!mapRef.current) {
          throw new Error('Контейнер карты не найден');
        }
        
        const newMap = new window.ymaps.Map(mapRef.current, {
          center: [38.5598, 68.7870], // Душанбе по умолчанию
          zoom: 10,
          controls: ['zoomControl', 'fullscreenControl']
        });

        if (!mountedRef.current) {
          console.log('⚠️ Компонент размонтирован во время создания карты');
          newMap.destroy();
          return;
        }

        console.log('✅ SingleAddressMap создана успешно');
        mapInstanceRef.current = newMap;
        setMapReady(true);
        setInitStatus('Карта готова к использованию!');
        console.log('🎉 SingleAddressMap полностью готова для отображения адресов');

      } catch (error) {
        if (!mountedRef.current) return;
        
        console.error('❌ Ошибка инициализации SingleAddressMap:', error);
        setError(`Ошибка загрузки карты: ${error.message}`);
        setInitStatus(`Ошибка: ${error.message}`);
      }
    };

    initMap();
  }, []);

  // Показ адреса на карте
  useEffect(() => {
    if (!mapInstanceRef.current || !address || !mapReady || !mountedRef.current) {
      return;
    }

    const showAddress = async () => {
      if (!mountedRef.current) return;
      
      setLoading(true);
      setError('');

      try {
        const ymaps = window.ymaps;
        if (!ymaps || !mountedRef.current) return;

        console.log(`🗺️ Показываем адрес на карте: "${address}"`);
        
        // Проверяем валидность адреса
        if (!address || address.length < 3) {
          throw new Error('Адрес слишком короткий или пустой');
        }

        // Очищаем карту
        mapInstanceRef.current.geoObjects.removeAll();

        // Геокодируем адрес
        const geocodeResult = await ymaps.geocode(address);
        const firstGeoObject = geocodeResult.geoObjects.get(0);

        if (!firstGeoObject) {
          throw new Error('Адрес не найден');
        }

        if (!mountedRef.current) return;

        // Получаем координаты
        const coords = firstGeoObject.geometry.getCoordinates();
        
        // Создаем маркер
        const placemark = new ymaps.Placemark(coords, {
          balloonContent: `<strong>${title}</strong><br/>${address}`,
          iconContent: 'П' // П - Получение
        }, {
          preset: 'islands#blueStretchyIcon'
        });

        if (!mountedRef.current || !mapInstanceRef.current) return;

        // Добавляем маркер на карту
        mapInstanceRef.current.geoObjects.add(placemark);
        
        // Центрируем карту на адресе
        mapInstanceRef.current.setCenter(coords, 15);
        
        console.log('✅ Адрес успешно отображен на карте');

      } catch (error) {
        if (mountedRef.current) {
          console.error('❌ Ошибка при отображении адреса:', error);
          
          let errorMessage = 'Не удалось найти адрес на карте.';
          if (error.message.includes('не найден') || error.message.includes('not found')) {
            errorMessage = 'Адрес не найден. Проверьте правильность адреса.';
          } else if (error.message.includes('короткий') || error.message.includes('пустой')) {
            errorMessage = 'Введите более точный адрес.';
          }
          
          setError(errorMessage);
        }
      } finally {
        if (mountedRef.current) {
          setLoading(false);
        }
      }
    };

    const debounceTimer = setTimeout(showAddress, 1000);
    return () => clearTimeout(debounceTimer);
  }, [mapInstanceRef.current, address, mapReady, title]);

  // Показываем состояние загрузки карты
  if (!mapReady) {
    return (
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex items-center space-x-2 mb-2">
          <MapPin className="h-5 w-5 text-blue-600" />
          <span className="font-medium text-blue-800">{title}</span>
        </div>
        <div className="text-sm text-blue-600">
          {initStatus}
        </div>
      </div>
    );
  }

  return (
    <div className="mt-4 border border-blue-200 rounded-lg overflow-hidden">
      {/* Заголовок карты */}
      <div className="bg-blue-50 px-4 py-2 border-b border-blue-200">
        <div className="flex items-center space-x-2">
          <MapPin className="h-5 w-5 text-blue-600" />
          <span className="font-medium text-blue-800">{title}</span>
        </div>
        {address && (
          <div className="text-sm text-blue-600 mt-1">
            📍 {address}
          </div>
        )}
      </div>

      {/* Статус */}
      {loading && (
        <div className="bg-yellow-50 px-4 py-2 border-b border-yellow-200">
          <div className="text-sm text-yellow-700">
            🔍 Поиск адреса на карте...
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 px-4 py-2 border-b border-red-200">
          <div className="text-sm text-red-700">
            ❌ {error}
          </div>
        </div>
      )}

      {/* Контейнер карты */}
      <div
        ref={mapRef}
        className="w-full h-64"
        style={{ minHeight: '256px' }}
      />
    </div>
  );
};

export default SingleAddressMap;