# Сторонние компоненты

Собственные уведомления и условия сторонних компонентов сохраняют силу. Установщики распространяются без изменения; принятие условий Python / Microsoft относится к установке. Исходный проект пользователя находится в original и не перелицензирован.

- Python: https://www.python.org/ ; исходники и PSF License: https://github.com/python/cpython/tree/v3.13.16
- Microsoft Visual C++ Redistributable: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist ; отдельные условия Microsoft, не open source. В архиве официальный установщик.
- Tesseract: https://github.com/tesseract-ocr/tesseract/tree/5.5.0 ; Windows-дистрибутив UB Mannheim, Apache-2.0. Оригинальный установщик и документы сохранены. Исходники сборки: https://github.com/UB-Mannheim/tesseract ; исходники движка: https://github.com/tesseract-ocr/tesseract/releases/tag/5.5.0 .
- DLL поставки Tesseract: уведомления в tesseract-distribution, условия каждого вложенного проекта действуют отдельно. GNU / LGPL-компоненты не становятся частью лицензии собственного кода SHIRA; ссылки на соответствующие исходники и лицензии содержатся в документах дистрибутива. Перед коммерческим распространением требуется отдельная лицензионная проверка полного набора DLL.
- Модели tessdata_fast: https://github.com/tesseract-ocr/tessdata_fast , Apache-2.0.
- ZXing-C++: https://github.com/zxing-cpp/zxing-cpp/tree/v2.3.0 , Apache-2.0.
- OpenCV: https://github.com/opencv/opencv/tree/4.11.0 ; лицензии и third-party, включая FFmpeg, сохранены из wheel opencv-python-headless.
- NumPy, Pillow, psutil, openpyxl, et_xmlfile: метаданные и лицензии рядом; версии перечислены в docs/dependencies.json. Уведомления из wheel сохранены без изменения.

Контрольные суммы компонентов приведены в SHA256SUMS.txt и docs/components.json. Хеш подтверждает целостность относительно этого комплекта, но сам по себе не доказывает доверенную подпись издателя. Sigstore-метаданные Python сохранены; криптографическая проверка Sigstore в этой среде не выполнялась.
