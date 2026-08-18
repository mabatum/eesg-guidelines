/* Настройка приёма замечаний.
 *
 * endpoint — адрес, куда уходят замечания. Подходит веб-приложение Google Apps
 * Script (замечания складываются в таблицу и при желании создают Issue на
 * GitHub) либо любая форма, принимающая POST.
 *
 * Пока endpoint пуст, кнопка «Замечание» открывает то же окно, но отправляет
 * письмо на адрес mailto — обратная связь работает и до настройки сервиса.
 *
 * contentType: 'text/plain' не вызывает предварительного запроса CORS и
 * подходит для Google Apps Script; для Formspree ставьте 'application/json'.
 */
window.EESG_FEEDBACK = {
  endpoint: '',
  contentType: 'text/plain;charset=utf-8',
  mailto: 'md.batov@gmail.com',
  project: 'EESG guidelines',
};
