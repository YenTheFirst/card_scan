(define (text_on_img filename out_file number)
  (let* (
		 (image (car (gimp-file-load RUN-NONINTERACTIVE filename filename)))
		 (drawable (car (gimp-image-get-active-layer image))))
	(let* (
		  (r (gimp-text-get-extents-fontname number 32 1 "USAAF_SERIAL_STENCIL"))
		  (clone_layer (car (gimp-layer-copy drawable FALSE))))
	  (gimp-image-add-layer image clone_layer 0)
	  (gimp-invert clone_layer)
	  (let ((text_layer (car (gimp-text-fontname image -1 (- 214 (/ (car r) 2)) (- 34 (cadr r)) number -1 FALSE 32 1 "USAAF_SERIAL_STENCIL"))))
		(gimp-selection-layer-alpha text_layer)
		(gimp-layer-add-mask clone_layer (car (gimp-layer-create-mask clone_layer ADD-SELECTION-MASK)))
		(gimp-image-remove-layer image text_layer))

	(gimp-image-flatten image)
	(set! drawable (car (gimp-image-get-active-layer image)))
	(gimp-file-save RUN-NONINTERACTIVE image drawable out_file out_file)
	(gimp-image-delete image))))
