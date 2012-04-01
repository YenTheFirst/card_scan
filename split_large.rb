=begin
end is 54 pt / 0.75 inch = 54px in large
first panel (pre-end) is 182 pt
total is 454 pt
height is 256 pt =  3.55.. inch = 256 px in large
3 main panels (front, end, back) = 418

x = 54 * index - 182
y = 0 
convert -extract 454x252+<x>+<y>
convert -extract 454x252-182+0 test_long.png -background red -extent 454x252-182+0 i_0.png

=end

def split_long(long_filename, split_base="i_", dir=".")
	#assumes measurements given above
	for index in (0...17)
		x = (56 * index - 182)
		geom = "418x252%+d+0" % x
		name = "%s/%s%02d.png" % [dir,split_base,index]
		out_geom = if x < 0
			geom
		else
			"418x252"
		end
		text = "%02x" % index
		#`convert -extract #{geom} '#{long_filename}' +repage -extent #{out_geom} -draw "text 182,151 '#{text}'" '#{name}'`
		`convert -extract #{geom} '#{long_filename}' +repage -extent #{out_geom} '#{name}'`
	end
end

def prepare_templates(split_base = "i_", out_base="out_", dir=".", range=(0...17))
	range.each_slice(2) do |nums|
		fnames = nums.map {|n| "%s/%s%02d.png" % [dir,split_base,n]}
		
		if nums.length == 2
			out_name = "%s/%s%02d_%02d.png" % [dir,out_base,*nums]
			`convert -size 612x792 xc:transparent -page +96+497 #{fnames[1]} -flop -flip -page +98+41 #{fnames[0]} -layers flatten #{out_name}`
		else
			out_name = "%s/%s%02d_none.png" % [dir, out_base, nums[0]]
			`convert -size 612x792 xc:transparent -page +98+41 #{fnames[0]} -layers flatten #{out_name}`
		end
	end
end

def add_numbers(split_base = "i_", out_base = "i_num_", dir = ".", offset = 0, range = (0...17))
	for index in range
		name = "%s/%s%02d.png" % [dir,split_base,index]
		out = "%s/%s%02d.png" % [dir,out_base,index]
		num = "%02d" % (index+offset)

		`gimp -i -b '(text_on_img "#{name}" "#{out}" "#{num}")' -b '(gimp-quit 0)'`
	end
end

#lpr -o scaling=100 out.png 
