import React, { useEffect, useRef, useState } from 'react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Alert, AlertDescription } from './ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { 
  MapPin, 
  Maximize2, 
  Minimize2, 
  ExternalLink, 
  RefreshCw,
  Navigation,
  AlertTriangle,
  CheckCircle,
  Package,
  Home,
  PowerOff,
  Clock,
  Phone,
  User,
  Truck,
  Filter
} from 'lucide-react';

const CourierTrackingMap = ({ userRole, apiCall }) => {
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [courierLocations, setCourierLocations] = useState([]);
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [statusFilter, setStatusFilter] = useState('all');
  const [refreshInterval, setRefreshInterval] = useState(null);
  const [activeCouriers, setActiveCouriers] = useState(0);

  // Определить цвет и иконку статуса курьера
  const getStatusConfig = (status) => {
    const configs = {
      'offline': {
        color: '#6B7280',
        bgColor: 'bg-gray-500',
        textColor: 'text-gray-700',
        icon: PowerOff,
        label: 'Не в сети'
      },
      'online': {
        color: '#10B981',
        bgColor: 'bg-green-500',
        textColor: 'text-green-700',
        icon: CheckCircle,
        label: 'Свободен'
      },
      'on_route': {
        color: '#3B82F6',
        bgColor: 'bg-blue-500',
        textColor: 'text-blue-700',
        icon: Navigation,
        label: 'Едет к клиенту'
      },
      'at_pickup': {
        color: '#F59E0B',
        bgColor: 'bg-orange-500',
        textColor: 'text-orange-700',
        icon: Package,
        label: 'На месте забора'
      },
      'at_delivery': {
        color: '#8B5CF6',
        bgColor: 'bg-purple-500',
        textColor: 'text-purple-700',
        icon: Home,
        label: 'На месте доставки'
      },
      'busy': {
        color: '#EF4444',
        bgColor: 'bg-red-500',
        textColor: 'text-red-700',
        icon: AlertTriangle,
        label: 'Занят'
      }
    };
    return configs[status] || configs['offline'];
  };

  // Загрузить местоположения курьеров
  const fetchCourierLocations = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const endpoint = userRole === 'admin' 
        ? '/api/admin/couriers/locations'
        : '/api/operator/couriers/locations';

      console.log(`Fetching courier locations from: ${endpoint}, User role: ${userRole}`);
      
      const response = await apiCall(endpoint, 'GET');
      
      console.log('Courier locations response:', response);
      
      if (response) {
        // Проверяем разные форматы ответа
        let locations = [];
        let activeCount = 0;
        
        if (response.locations && Array.isArray(response.locations)) {
          // Стандартный формат: {locations: [...], active_couriers: N}
          locations = response.locations;
          activeCount = response.active_couriers || 0;
        } else if (Array.isArray(response)) {
          // Прямой массив курьеров
          locations = response;
          activeCount = locations.filter(l => l.status !== 'offline').length;
        } else {
          console.warn('Unexpected response format:', response);
        }
        
        console.log(`Found ${locations.length} courier locations, ${activeCount} active`);
        
        setCourierLocations(locations);
        setActiveCouriers(activeCount);
        setLastUpdated(new Date());
      } else {
        console.warn('Empty response from courier locations endpoint');
        setCourierLocations([]);
        setActiveCouriers(0);
      }
    } catch (error) {
      console.error('Error fetching courier locations:', error);
      setError(`Ошибка загрузки местоположений: ${error.message}`);
      setCourierLocations([]);
      setActiveCouriers(0);
    } finally {
      setIsLoading(false);
    }
  };

  // Загрузка скрипта Яндекс.Карт
  const loadYandexMapsScript = () => {
    return new Promise((resolve, reject) => {
      if (window.ymaps) {
        resolve();
        return;
      }

      const script = document.createElement('script');
      const apiKey = process.env.REACT_APP_YANDEX_MAPS_API_KEY;
      script.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`;
      script.type = 'text/javascript';
      
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Не удалось загрузить Яндекс.Карты'));

      document.head.appendChild(script);
    });
  };

  // Инициализация карты
  const initMap = async () => {
    if (!mapRef.current || !window.ymaps) return;

    setIsLoading(true);
    setError(null);

    try {
      // Очистить предыдущую карту
      if (mapInstanceRef.current) {
        mapInstanceRef.current.destroy();
        mapInstanceRef.current = null;
      }

      // Центр карты - Москва по умолчанию
      let center = [55.751244, 37.618423];
      let zoom = 10;

      // Фильтровать курьеров по статусу
      const filteredCouriers = statusFilter === 'all' 
        ? courierLocations
        : courierLocations.filter(courier => courier.status === statusFilter);

      // Если есть курьеры, центрировать на первом
      if (filteredCouriers.length > 0) {
        const firstCourier = filteredCouriers[0];
        center = [firstCourier.latitude, firstCourier.longitude];
        zoom = filteredCouriers.length === 1 ? 16 : 12;
      }

      // Создать карту
      const map = new window.ymaps.Map(mapRef.current, {
        center: center,
        zoom: zoom,
        controls: ['zoomControl', 'typeSelector', 'fullscreenControl']
      });

      mapInstanceRef.current = map;

      // Добавить маркеры для всех курьеров
      filteredCouriers.forEach((courier, index) => {
        const statusConfig = getStatusConfig(courier.status);
        const coordinates = [courier.latitude, courier.longitude];
        
        // Создать маркер
        const placemark = new window.ymaps.Placemark(coordinates, {
          balloonContent: `
            <div style="max-width: 350px; font-family: system-ui;">
              <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <div style="width: 12px; height: 12px; background-color: ${statusConfig.color}; border-radius: 50%; margin-right: 8px;"></div>
                <h4 style="margin: 0; font-size: 16px; font-weight: bold; color: #1F2937;">
                  ${courier.courier_name}
                </h4>
              </div>
              
              <div style="background: #F9FAFB; padding: 12px; border-radius: 8px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                  <span style="font-weight: 600; color: #374151; margin-right: 8px;">Статус:</span>
                  <span style="color: ${statusConfig.color}; font-weight: 500;">${statusConfig.label}</span>
                </div>
                
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                  <span style="font-weight: 600; color: #374151; margin-right: 8px;">Транспорт:</span>
                  <span style="color: #6B7280;">${courier.transport_type}</span>
                </div>
                
                <div style="display: flex; align-items: center; margin-bottom: 6px;">
                  <span style="font-weight: 600; color: #374151; margin-right: 8px;">📞 Телефон:</span>
                  <span style="color: #6B7280;">${courier.courier_phone}</span>
                </div>
                
                ${courier.current_request_id ? `
                  <div style="display: flex; align-items: center; margin-bottom: 6px;">
                    <span style="font-weight: 600; color: #374151; margin-right: 8px;">📦 Заявка:</span>
                    <span style="color: #3B82F6;">#${courier.current_request_id.slice(-6)}</span>
                  </div>
                ` : ''}
                
                ${courier.current_request_address ? `
                  <div style="display: flex; align-items: flex-start; margin-bottom: 6px;">
                    <span style="font-weight: 600; color: #374151; margin-right: 8px;">📍 Адрес заявки:</span>
                    <span style="color: #6B7280; line-height: 1.4;">${courier.current_request_address}</span>
                  </div>
                ` : ''}
              </div>
              
              <div style="font-size: 12px; color: #9CA3AF; text-align: center;">
                Обновлено: ${courier.time_since_update || 'недавно'}
              </div>
            </div>
          `,
          hintContent: `${courier.courier_name} - ${statusConfig.label}`
        }, {
          preset: 'islands#dotIcon',
          iconColor: statusConfig.color
        });
        
        map.geoObjects.add(placemark);
      });

      // Подстроить границы карты под все маркеры
      if (filteredCouriers.length > 1) {
        const bounds = map.geoObjects.getBounds();
        if (bounds) {
          map.setBounds(bounds, { checkZoomRange: true, zoomMargin: 50 });
        }
      }

      setIsLoading(false);
    } catch (error) {
      console.error('Ошибка инициализации карты:', error);
      setError('Ошибка загрузки карты');
      setIsLoading(false);
    }
  };

  // Запуск автообновления
  const startAutoRefresh = () => {
    if (refreshInterval) return;
    
    const interval = setInterval(() => {
      fetchCourierLocations();
    }, 30000); // 30 секунд
    
    setRefreshInterval(interval);
  };

  // Остановка автообновления
  const stopAutoRefresh = () => {
    if (refreshInterval) {
      clearInterval(refreshInterval);
      setRefreshInterval(null);
    }
  };

  // Эффект для загрузки данных
  useEffect(() => {
    if (isMapOpen) {
      fetchCourierLocations();
      startAutoRefresh();
    } else {
      stopAutoRefresh();
    }

    return () => stopAutoRefresh();
  }, [isMapOpen]);

  // Эффект для инициализации карты
  useEffect(() => {
    if (isMapOpen && courierLocations.length > 0) {
      loadYandexMapsScript()
        .then(() => {
          if (window.ymaps) {
            window.ymaps.ready(() => {
              initMap();
            });
          }
        })
        .catch((err) => {
          setError(err.message);
          setIsLoading(false);
        });
    }
  }, [isMapOpen, courierLocations, statusFilter]);

  // Очистка при размонтировании - ИСПРАВЛЕНИЕ для removeChild ошибки
  useEffect(() => {
    return () => {
      // Добавляем задержку для безопасной очистки
      setTimeout(() => {
        try {
          if (mapInstanceRef.current) {
            // Сначала удаляем все geoObjects
            if (mapInstanceRef.current.geoObjects) {
              mapInstanceRef.current.geoObjects.removeAll();
            }
            mapInstanceRef.current.destroy();
            mapInstanceRef.current = null;
          }
          
          stopAutoRefresh();
        } catch (error) {
          console.warn('Предупреждение при очистке CourierTrackingMap:', error);
        }
      }, 0);
    };
  }, []);

  // Форматировать время последнего обновления
  const formatLastUpdate = () => {
    if (!lastUpdated) return 'Никогда';
    
    const now = new Date();
    const diff = Math.floor((now - lastUpdated) / 1000);
    
    if (diff < 60) return 'только что';
    if (diff < 3600) return `${Math.floor(diff / 60)} мин назад`;
    return lastUpdated.toLocaleTimeString('ru-RU');
  };

  // Фильтрованные курьеры для статистики
  const filteredCouriers = statusFilter === 'all' 
    ? courierLocations
    : courierLocations.filter(courier => courier.status === statusFilter);

  return (
    <Card className="w-full">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-full bg-blue-500">
              <MapPin className="h-5 w-5 text-white" />
            </div>
            <div>
              <CardTitle className="text-lg">Отслеживание курьеров</CardTitle>
              <CardDescription>Real-time местоположение всех курьеров</CardDescription>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <Badge variant="default" className="bg-green-500">
              {activeCouriers} активных
            </Badge>
            <Badge variant="secondary">
              {courierLocations.length} всего
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Кнопки управления */}
        <div className="flex flex-wrap gap-2">
          <Button 
            onClick={() => setIsMapOpen(!isMapOpen)}
            variant={isMapOpen ? "default" : "outline"}
            className={isMapOpen ? 'bg-blue-600 hover:bg-blue-700' : ''}
          >
            <MapPin className="mr-2 h-4 w-4" />
            {isMapOpen ? 'Скрыть карту' : 'Показать карту'}
          </Button>
          
          <Button 
            onClick={fetchCourierLocations}
            variant="outline"
            disabled={isLoading}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
            Обновить
          </Button>
          
          <Button
            onClick={() => {
              const allAddresses = courierLocations.map(c => 
                `${c.courier_name}: ${c.latitude},${c.longitude}`
              ).join(' | ');
              const encodedAddresses = encodeURIComponent(allAddresses);
              const yandexMapsUrl = `https://yandex.ru/maps/?text=${encodedAddresses}&mode=search`;
              window.open(yandexMapsUrl, '_blank');
            }}
            variant="outline"
          >
            <ExternalLink className="mr-2 h-4 w-4" />
            Открыть в Яндекс.Картах
          </Button>
        </div>

        {/* Фильтр по статусу */}
        <div className="flex items-center space-x-2">
          <Filter className="h-4 w-4 text-gray-500" />
          <label className="text-sm font-medium text-gray-700">Фильтр по статусу:</label>
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Все курьеры ({courierLocations.length})</SelectItem>
              <SelectItem value="online">
                <div className="flex items-center">
                  <CheckCircle className="mr-2 h-4 w-4 text-green-500" />
                  Свободен ({courierLocations.filter(c => c.status === 'online').length})
                </div>
              </SelectItem>
              <SelectItem value="on_route">
                <div className="flex items-center">
                  <Navigation className="mr-2 h-4 w-4 text-blue-500" />
                  Едет к клиенту ({courierLocations.filter(c => c.status === 'on_route').length})
                </div>
              </SelectItem>
              <SelectItem value="at_pickup">
                <div className="flex items-center">
                  <Package className="mr-2 h-4 w-4 text-orange-500" />
                  На месте забора ({courierLocations.filter(c => c.status === 'at_pickup').length})
                </div>
              </SelectItem>
              <SelectItem value="at_delivery">
                <div className="flex items-center">
                  <Home className="mr-2 h-4 w-4 text-purple-500" />
                  На месте доставки ({courierLocations.filter(c => c.status === 'at_delivery').length})
                </div>
              </SelectItem>
              <SelectItem value="busy">
                <div className="flex items-center">
                  <AlertTriangle className="mr-2 h-4 w-4 text-red-500" />
                  Занят ({courierLocations.filter(c => c.status === 'busy').length})
                </div>
              </SelectItem>
              <SelectItem value="offline">
                <div className="flex items-center">
                  <PowerOff className="mr-2 h-4 w-4 text-gray-500" />
                  Не в сети ({courierLocations.filter(c => c.status === 'offline').length})
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Статистика */}
        <div className="bg-gray-50 p-3 rounded-lg">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center">
              <Clock className="mr-2 h-4 w-4 text-gray-500" />
              <span className="font-medium">Последнее обновление:</span>
              <span className="ml-2">{formatLastUpdate()}</span>
            </div>
            <div className="flex items-center">
              <span className="font-medium">Показано:</span>
              <span className="ml-2">{filteredCouriers.length} из {courierLocations.length}</span>
            </div>
          </div>
        </div>

        {/* Контейнер карты */}
        {isMapOpen && (
          <div className="border border-blue-200 rounded-lg overflow-hidden">
            <div className="bg-blue-50 px-4 py-3 border-b border-blue-200">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <MapPin className="h-5 w-5 text-blue-600" />
                  <h3 className="font-medium text-blue-800">
                    Карта курьеров ({filteredCouriers.length})
                  </h3>
                </div>
              </div>
            </div>

            <div className="relative">
              {isLoading && (
                <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center z-10">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                    <p className="text-sm text-gray-600">Загрузка карты...</p>
                  </div>
                </div>
              )}

              {error && (
                <div className="absolute inset-0 bg-red-50 flex items-center justify-center z-10">
                  <div className="text-center">
                    <MapPin className="h-8 w-8 text-red-400 mx-auto mb-2" />
                    <p className="text-sm text-red-600">{error}</p>
                    <Button
                      onClick={() => {
                        setError(null);
                        fetchCourierLocations();
                      }}
                      variant="outline"
                      size="sm"
                      className="mt-2 text-red-600 border-red-300"
                    >
                      Попробовать снова
                    </Button>
                  </div>
                </div>
              )}

              <div
                ref={mapRef}
                className="w-full h-96"
                style={{ minHeight: '500px' }}
              />
            </div>

            <div className="bg-blue-50 px-4 py-2 border-t border-blue-200">
              <p className="text-xs text-blue-600">
                💡 Нажмите на маркер для просмотра деталей курьера • 
                Автообновление каждые 30 секунд • 
                Используйте фильтр для выбора статуса
              </p>
            </div>
          </div>
        )}

        {/* Ошибки */}
        {error && !isMapOpen && (
          <Alert className="border-red-200 bg-red-50">
            <AlertTriangle className="h-4 w-4 text-red-600" />
            <AlertDescription className="text-red-700">
              {error}
            </AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default CourierTrackingMap;